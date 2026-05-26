#!/usr/bin/env python3
"""MyTV 本地 CORS 代理服务器 - 零依赖，纯标准库"""

import http.server
import urllib.request
import urllib.error
import urllib.parse
import sys
import socket
import os
import ssl
import json
import time

PROXY_PORT = 8799
TIMEOUT = 15  # 单次请求超时秒数
MAX_RETRIES = 3  # 上游请求最大重试次数
RETRY_DELAY = 1  # 重试间隔秒数

# 备选 User-Agent 列表，应对反爬
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# 创建宽松 SSL 上下文（允许自签名证书）
try:
    _ssl_ctx = ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = ssl.CERT_NONE
except Exception:
    _ssl_ctx = None


def find_free_port(start=8799, end=8809):
    """自动查找可用端口"""
    for port in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return None


class CORSProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # 从 path 或 query 中提取目标 URL
        target_url = None
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        # 方式1: ?url=xxx 参数
        if "url" in qs:
            target_url = qs["url"][0]

        # 方式2: 路径去掉 / 后即为编码后的URL
        if not target_url:
            path = self.path.lstrip("/")
            if path and path.startswith("http"):
                target_url = path

        # 健康检查
        if self.path == "/health" or self.path == "/":
            self._send_json({"status": "ok", "port": PROXY_PORT, "usage": "GET /?url=ENCODED_URL"})
            return

        if not target_url:
            self._send_json({"status": "error", "message": "缺少 url 参数，用法: /?url=编码后的URL"}, 400)
            return

        # URL 可能被双重编码，尝试 decode
        try:
            target_url = urllib.parse.unquote(target_url)
        except Exception:
            pass

        # 带重试的上游请求
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                ua = USER_AGENTS[attempt % len(USER_AGENTS)]
                req = urllib.request.Request(
                    target_url,
                    headers={
                        "User-Agent": ua,
                        "Accept": "*/*",
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
                        "Connection": "close",
                    },
                )
                context = _ssl_ctx if target_url.startswith("https") else None
                with urllib.request.urlopen(req, timeout=TIMEOUT, context=context) as resp:
                    body = resp.read()
                    content_type = resp.headers.get("Content-Type", "application/octet-stream")

                    self.send_response(200)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                    self.send_header("Access-Control-Allow-Headers", "*")
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    self.wfile.write(body)
                    return  # 成功，直接返回

            except urllib.error.HTTPError as e:
                last_error = e
                # 对于 4xx 客户端错误不重试，5xx 服务器错误可重试
                if e.code and 400 <= e.code < 500:
                    break
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
            except urllib.error.URLError as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue

        # 所有重试均失败
        if isinstance(last_error, urllib.error.HTTPError):
            # 尝试读取上游返回的错误 body
            try:
                err_body = last_error.read().decode("utf-8", errors="replace")[:200]
            except Exception:
                err_body = ""
            self._send_json({
                "status": "error",
                "message": f"上游返回 HTTP {last_error.code}",
                "code": last_error.code,
                "upstream_url": target_url,
                "detail": err_body,
            }, 502)
        elif isinstance(last_error, urllib.error.URLError):
            self._send_json({
                "status": "error",
                "message": f"无法连接上游: {last_error.reason}",
                "upstream_url": target_url,
            }, 502)
        else:
            self._send_json({"status": "error", "message": str(last_error), "upstream_url": target_url}, 500)

    def do_OPTIONS(self):
        """CORS 预检请求"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """精简日志输出"""
        if "/health" not in self.path:
            sys.stdout.write(f"[代理] {args[0]}\n")
            sys.stdout.flush()


def main():
    global PROXY_PORT
    port = find_free_port(PROXY_PORT)
    if port is None:
        print(f"[错误] 端口 {PROXY_PORT}-8809 均被占用，无法启动代理")
        sys.exit(1)

    PROXY_PORT = port
    server = http.server.HTTPServer(("127.0.0.1", port), CORSProxyHandler)

    # 写出端口文件供 start.bat 和 HTML 读取
    port_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".proxy_port")
    with open(port_file, "w") as f:
        f.write(str(port))

    print(f"[代理] CORS 代理已启动: http://127.0.0.1:{port}")
    print(f"[代理] 用法: http://127.0.0.1:{port}/?url=ENCODED_URL")
    print(f"[代理] 端口文件: {port_file}")
    print(f"[代理] 按 Ctrl+C 停止")
    sys.stdout.flush()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[代理] 已停止")
        server.server_close()
        # 清理端口文件
        try:
            port_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".proxy_port")
            if os.path.exists(port_file):
                os.remove(port_file)
        except Exception:
            pass


if __name__ == "__main__":
    main()
