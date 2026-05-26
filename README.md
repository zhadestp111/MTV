# 便携电视播放器 (Portable TV Player)

纯单文件 HTML IPTV 播放器，支持 M3U/TXT 直播源，双击即用。

## 功能特性

- **多格式支持**: M3U 标准格式、TVbox 格式(#genre#)、TXT 格式
- **多协议**: HLS (m3u8)、RTMP、HTTP-FLV、P2P 等
- **键盘操作**: ↑↓ 换台、←→ 换分组、0-9 数字选台、F 收藏、Space 暂停
- **持久化**: localStorage 保存配置、收藏、上次播放频道
- **线路检测**: 自动检测多线路可用性，可视化状态显示
- **播放诊断**: 自动诊断播放失败原因（编码/超时/网络/HLS错误）并尝试修复
- **视频录制**: 支持下载录制当前播放内容（三级降级策略）
- **CORS 代理**: Python 零依赖本地代理 (8799 端口)

## 快速开始

### Windows
双击 `start.bat` 一键启动代理服务并打开播放器。

### 手动启动
```bash
# 1. 启动 CORS 代理
python proxy-server.py

# 2. 用浏览器打开 tv-player.html
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `tv-player.html` | 主播放器（单文件，含全部 CSS/JS） |
| `proxy-server.py` | Python 本地 CORS 代理（零依赖） |
| `start.bat` | Windows 一键启动脚本 |

## 参考

基于 [yaoxieyoulei/mytv-android](https://github.com/yaoxieyoulei/mytv-android) 设计理念创建。
