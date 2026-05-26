import sys

path = r'D:\AI自制工具\便携电视播放器\tv-player.html'

with open(path, 'rb') as f:
    data = f.read()

# Boundaries  
comment_start = 86546  # Start of download section comment
merge_pos = data.find(b'function mergeAndSave()')

print(f"Replacing bytes {comment_start} to {merge_pos}")

# Build clean replacement code
clean_code = b'''/* ---------- \xe4\xb8\x8b\xe8\xbd\xbd\xef\xbc\x88\xe5\x8f\x8c\xe6\xa8\xa1\xe5\xbc\x8f: HLS\xe5\x88\x86\xe7\x89\x87 / \xe7\x9b\xb4\xe8\xbf\x9e\xe6\xb5\x81\xef\xbc\x89 ---------- */
/* HLS(m3u8): \xe8\xa7\xa3\xe6\x9e\x90m3u8 \xe2\x86\x92 \xe9\x80\x90\xe4\xb8\xaa\xe4\xb8\x8b\xe8\xbd\xbdTS\xe5\x88\x86\xe7\x89\x87 \xe2\x86\x92 \xe5\x90\x88\xe5\xb9\xb6 \xe2\x86\x92 \xe5\x8e\x9f\xe5\xa7\x8b\xe7\x94\xbb\xe8\xb4\xa8\xe9\x9b\xb6\xe6\x8d\x9f\xe8\x80\x97
   \xe9\x9d\x9eHLS(mp4/flv/ts\xe7\xad\x89): \xe7\x9b\xb4\xe6\x8e\xa5fetch\xe6\xb5\x81\xe4\xb8\x8b\xe8\xbd\xbd \xe2\x86\x92 \xe9\x9b\xb6\xe6\x92\xad\xe6\x94\xbe\xe5\xbd\xb1\xe5\x93\x8d\xe3\x80\x81\xe9\x9b\xb6CPU\xe5\xbd\x95\xe5\x88\xb6\xe5\xbc\x80\xe9\x94\x80
   \xe7\x9b\xb4\xe6\x92\xad\xe6\xb5\x81: \xe8\xbd\xae\xe8\xaf\xa2m3u8\xe6\x8c\x81\xe7\xbb\xad\xe6\x8a\x93\xe6\x96\xb0\xe5\x88\x86\xe7\x89\x87 / \xe7\x9b\xb4\xe8\xbf\x9e\xe6\x8c\x81\xe7\xbb\xad\xe8\xaf\xbb\xe5\x8f\x96\xe6\xb5\x81\xe7\x9b\xb4\xe5\x88\xb0\xe5\x81\x9c\xe6\xad\xa2
   VOD \xe7\x82\xb9\xe6\x92\xad: \xe4\xb8\x80\xe6\xac\xa1\xe6\x80\xa7\xe4\xb8\x8b\xe8\xbd\xbd\xe5\xae\x8c\xe6\xaf\x95\xe5\x90\x8e\xe8\x87\xaa\xe5\x8a\xa8\xe4\xbf\x9d\xe5\xad\x98 */
function toggleDownload() {
  if (state.dlActive) {
    stopDownload(true);
  } else {
    startDownload();
  }
}

function startDownload() {
  var streamUrl = "";
  if (state.hls && state.hls.url) {
    streamUrl = state.hls.url;
  } else if (state.curChanIdx >= 0) {
    var ch = state.allChannels[state.curChanIdx];
    streamUrl = ch.urls[state.curLineIdx] || ch.urls[0];
  }
  if (!streamUrl) {
    showToast("\xe6\x97\xa0\xe6\xb3\x95\xe8\x8e\xb7\xe5\x8f\x96\xe6\x92\xad\xe6\x94\xbe\xe5\x9c\xb0\xe5\x9d\x80", "error"); return;
  }

  var isHLS = /\.m3u8(\?|$)/i.test(streamUrl) || /\/m3u8/i.test(streamUrl);

  state.dlActive = true;
  state.dlStartTime = Date.now();
  state.dlChunks = [];

  // UI
  $("download-btn").classList.add("recording");
  $("download-btn").innerHTML = '<span id="rec-dot"></span>\xe5\x81\x9c\xe6\xad\xa2';
  $("rec-indicator").classList.add("show");
  $("rec-timer").textContent = "00:00";
  $("dl-progress").textContent = "";
  updateDlTimer();
  state.dlTimerId = setInterval(updateDlTimer, 1000);

  if (isHLS) {
    state.dlMode = "hls";
    state.dlAborter = new AbortController();
    state.dlTotalSegments = 0;
    state.dlDownloadedSegments = 0;
    state.dlSeenUrls = {};
    state.dlM3u8Url = streamUrl;
    showToast("\xe5\xbc\x80\xe5\xa7\x8b\xe4\xb8\x8b\xe8\xbd\xbd\xe5\x88\x86\xe7\x89\x87 (HLS)...", "success");
    downloadLoop(streamUrl);
  } else {
    state.dlMode = "direct";
    state.dlAborter = new AbortController();
    state.dlDownloadedSize = 0;
    state.dlContentType = "";
    showToast("\xe5\xbc\x80\xe5\xa7\x8b\xe4\xb8\x8b\xe8\xbd\xbd (\xe7\x9b\xb4\xe8\xbf\x9e)...", "success");
    fetchDirect(streamUrl);
  }
}

function stopDownload(save) {
  state.dlActive = false;

  if (state.dlAborter) {
    try { state.dlAborter.abort(); } catch(e) {}
    state.dlAborter = null;
  }
  if (state.dlPollTimerId) { clearTimeout(state.dlPollTimerId); state.dlPollTimerId = null; }
  if (state.dlTimerId) { clearInterval(state.dlTimerId); state.dlTimerId = null; }

  $("download-btn").classList.remove("recording");
  $("download-btn").innerHTML = '<span id="rec-dot"></span>\xe4\xb8\x8b\xe8\xbd\xbd';
  $("rec-indicator").classList.remove("show");

  if (save && state.dlChunks.length > 0) {
    mergeAndSave();
  } else if (save) {
    showToast("\xe6\xb2\xa1\xe6\x9c\x89\xe4\xb8\x8b\xe8\xbd\xbd\xe5\x88\xb0\xe4\xbb\xbb\xe4\xbd\x95\xe6\x95\xb0\xe6\x8d\xae", "warn");
  }

  state.dlChunks = [];
  state.dlTotalSegments = 0;
  state.dlDownloadedSegments = 0;
  state.dlDownloadedSize = 0;
  state.dlStartTime = null;
  state.dlSeenUrls = null;
  state.dlM3u8Url = "";
  state.dlContentType = "";
  state.dlMode = "";
}
'''

# More blocks...
clean_code += b'''
/* ===== \xe7\x9b\xb4\xe8\xbf\x9e\xe4\xb8\x8b\xe8\xbd\xbd: \xe9\x9d\x9eHLS\xe6\xb5\x81\xe7\x9b\xb4\xe6\x8e\xa5fetch \xe2\x86\x92 \xe9\x9b\xb6\xe6\x92\xad\xe6\x94\xbe\xe5\xbd\xb1\xe5\x93\x8d\xe3\x80\x81\xe9\x9b\xb6CPU\xe5\xbd\x95\xe5\x88\xb6\xe5\xbc\x80\xe9\x94\x80 ===== */
/* \xe9\x80\x82\xe7\x94\xa8: mp4/flv/ts\xe7\xad\x89\xe7\x9b\xb4\xe9\x93\xbe\xe6\x96\x87\xe4\xbb\xb6\xe6\x88\x96HTTP\xe6\xb5\x81
   \xe7\x9b\xb4\xe6\x92\xad: \xe6\x8c\x81\xe7\xbb\xad\xe8\xaf\xbb\xe5\x8f\x96response body\xe7\x9b\xb4\xe5\x88\xb0\xe7\x94\xa8\xe6\x88\xb7\xe5\x81\x9c\xe6\xad\xa2
   VOD: \xe4\xb8\x8b\xe8\xbd\xbd\xe5\xae\x8c\xe6\xaf\x95\xe8\x87\xaa\xe5\x8a\xa8\xe4\xbf\x9d\xe5\xad\x98 */
function fetchDirect(url) {
  if (typeof fetch !== "function") {
    showToast("\xe6\xb5\x8f\xe8\xa7\x88\xe5\x99\xa8\xe4\xb8\x8d\xe6\x94\xaf\xe6\x8c\x81fetch, \xe6\x97\xa0\xe6\xb3\x95\xe4\xb8\x8b\xe8\xbd\xbd", "error");
    forceCleanDl(); return;
  }

  var signal = state.dlAborter ? state.dlAborter.signal : null;

  fetch(url, { signal: signal, cache: "no-store" })
    .then(function(r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      if (!r.body) throw new Error("\xe5\x93\x8d\xe5\xba\x94\xe6\x97\xa0body(\xe5\x8f\xaf\xe8\x83\xbd\xe6\x98\xafWebRTC/RTMP, \xe4\xb8\x8d\xe6\x94\xaf\xe6\x8c\x81\xe7\x9b\xb4\xe8\xbf\x9e\xe4\xb8\x8b\xe8\xbd\xbd)");

      state.dlContentType = r.headers.get("Content-Type") || "";
      var reader = r.body.getReader();
      return pumpStream(reader);
    })
    .then(function() {
      if (state.dlActive) stopDownload(true);
    })
    .catch(function(err) {
      if (!state.dlActive || err.name === "AbortError") return;
      console.error("[MyTV] Direct download failed:", err.message);
      showToast("\xe4\xb8\x8b\xe8\xbd\xbd\xe5\xa4\xb1\xe8\xb4\xa5: " + err.message, "error");
      forceCleanDl();
    });
}

/* \xe4\xbb\x8e ReadableStream \xe6\x8c\x81\xe7\xbb\xad\xe8\xaf\xbb\xe5\x8f\x96\xe6\x95\xb0\xe6\x8d\xae\xe5\x9d\x97 */
function pumpStream(reader) {
  return reader.read().then(function(result) {
    if (result.done) return;
    if (!state.dlActive) {
      try { reader.cancel(); } catch(e) {}
      return;
    }

    var chunk = new Uint8Array(result.value);
    state.dlChunks.push(chunk);
    state.dlDownloadedSize += chunk.length;
    updateDlProgress();

    return pumpStream(reader);
  });
}

/* \xe5\xbc\xba\xe5\x88\xb6\xe6\xb8\x85\xe7\x90\x86\xe4\xb8\x8b\xe8\xbd\xbd\xe7\x8a\xb6\xe6\x80\x81 */
function forceCleanDl() {
  if (state.dlAborter) { try { state.dlAborter.abort(); } catch(e) {} state.dlAborter = null; }
  if (state.dlPollTimerId) { clearTimeout(state.dlPollTimerId); state.dlPollTimerId = null; }
  if (state.dlTimerId) { clearInterval(state.dlTimerId); state.dlTimerId = null; }

  $("download-btn").classList.remove("recording");
  $("download-btn").innerHTML = '<span id="rec-dot"></span>\xe4\xb8\x8b\xe8\xbd\xbd';
  $("rec-indicator").classList.remove("show");

  state.dlActive = false; state.dlMode = "";
  state.dlChunks = []; state.dlStartTime = null;
  state.dlDownloadedSize = 0; state.dlContentType = "";
}

/* \xe4\xb8\xbb\xe4\xb8\x8b\xe8\xbd\xbd\xe5\xbe\xaa\xe7\x8e\xaf: \xe6\x8b\x89 m3u8 \xe2\x86\x92 \xe8\xa7\xa3\xe6\x9e\x90\xe5\x88\x86\xe7\x89\x87 \xe2\x86\x92 \xe4\xb8\x8b\xe8\xbd\xbd\xe6\x96\xb0\xe5\x88\x86\xe7\x89\x87 \xe2\x86\x92 VOD\xe5\xae\x8c\xe6\x88\x90\xe6\x88\x96\xe7\x9b\xb4\xe6\x92\xad\xe8\xbd\xae\xe8\xaf\xa2 */
function downloadLoop(m3u8Url) {
  if (!state.dlActive) return;

  var signal = state.dlAborter ? state.dlAborter.signal : null;

  fetch(m3u8Url, { signal: signal })
    .then(function(r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.text();
    })
    .then(function(content) {
      if (!state.dlActive) return;

      var segments = parseM3U(content, m3u8Url);
      if (!segments || !segments.length) {
        console.warn("[MyTV] No TS segments found in playlist");
        schedulePoll(m3u8Url, 3000);
        return;
      }

      var isLive = !/#EXT-X-ENDLIST/i.test(content);

      var newSegments = [];
      for (var i = 0; i < segments.length; i++) {
        var segUrl = segments[i];
        if (!state.dlSeenUrls[segUrl]) {
          newSegments.push(segUrl);
          state.dlSeenUrls[segUrl] = true;
        }
      }

      state.dlTotalSegments = Math.max(state.dlTotalSegments, segments.length);

      if (newSegments.length === 0) {
        if (isLive) {
          schedulePoll(m3u8Url, 3000);
        } else {
          stopDownload(true);
        }
        return;
      }

      downloadNextBatch(newSegments, 0, signal, function(success) {
        if (!state.dlActive) return;

        updateDlProgress();

        if (isLive) {
          var delay = success ? 2000 : 4000;
          schedulePoll(m3u8Url, delay);
        } else {
          if (state.dlDownloadedSegments >= state.dlTotalSegments) {
            stopDownload(true);
          } else {
            schedulePoll(m3u8Url, 1000);
          }
        }
      });
    })
    .catch(function(err) {
      if (!state.dlActive) return;
      if (err.name === "AbortError") return;

      console.error("[MyTV] m3u8 fetch failed:", err.message);
      if (state.dlActive) {
        schedulePoll(m3u8Url, 5000);
      }
    });
}

/* \xe9\x80\x90\xe4\xb8\xaa\xe4\xb8\x8b\xe8\xbd\xbd\xe5\x88\x86\xe7\x89\x87\xef\xbc\x88\xe4\xb8\xb2\xe8\xa1\x8c\xef\xbc\x8c\xe9\x81\xbf\xe5\x85\x8d\xe5\x8e\x8b\xe5\x9e\xae\xe6\x9c\x8d\xe5\x8a\xa1\xe5\x99\xa8\xef\xbc\x89 */
function downloadNextBatch(urls, idx, signal, callback) {
  if (idx >= urls.length || !state.dlActive) {
    callback(true);
    return;
  }

  var url = urls[idx];
  if (url.length < 4) {
    state.dlDownloadedSegments++;
    downloadNextBatch(urls, idx + 1, signal, callback);
    return;
  }

  fetch(url, { signal: signal })
    .then(function(r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.arrayBuffer();
    })
    .then(function(buf) {
      if (!state.dlActive) return;
      state.dlChunks.push({ url: url, data: new Uint8Array(buf) });
      state.dlDownloadedSegments++;
      updateDlProgress();
      downloadNextBatch(urls, idx + 1, signal, callback);
    })
    .catch(function(err) {
      if (!state.dlActive) return;
      if (err.name === "AbortError") return;

      console.warn("[MyTV] Segment download failed (" + (idx+1) + "/" + urls.length + "):", err.message);
      downloadNextBatch(urls, idx + 1, signal, callback);
    });
}

/* \xe5\xae\x89\xe6\x8e\x92\xe4\xb8\x8b\xe6\xac\xa1\xe8\xbd\xae\xe8\xaf\xa2 m3u8 */
function schedulePoll(m3u8Url, delay) {
  if (!state.dlActive) return;
  if (state.dlPollTimerId) clearTimeout(state.dlPollTimerId);
  state.dlPollTimerId = setTimeout(function() {
    state.dlPollTimerId = null;
    downloadLoop(m3u8Url);
  }, delay || 3000);
}

/* \xe8\xa7\xa3\xe6\x9e\x90 m3u8 \xe6\x92\xad\xe6\x94\xbe\xe5\x88\x97\xe8\xa1\xa8\xef\xbc\x8c\xe8\xbf\x94\xe5\x9b\x9e TS \xe5\x88\x86\xe7\x89\x87 URL \xe6\x95\xb0\xe7\xbb\x84 */
function parseM3U(content, baseUrl) {
  var lines = content.split(/\r?\n/);
  var segments = [];
  for (var i = 0; i < lines.length; i++) {
    var line = lines[i].trim();
    if (!line || line[0] === "#") continue;
    if (/\.ts(\?.*)?$/i.test(line)) {
      segments.push(resolveUrl(line, baseUrl));
    }
  }
  return segments;
}

/* \xe8\xa7\xa3\xe6\x9e\x90\xe7\x9b\xb8\xe5\xaf\xb9 URL */
function resolveUrl(url, base) {
  if (/^https?:\/\//i.test(url)) return url;
  if (url[0] === "/") {
    var m = base.match(/^(https?:\/\/[^\/]+)/);
    return (m ? m[1] : "") + url;
  }
  var baseClean = base.replace(/\?.*$/, "").replace(/\/[^\/]*$/, "");
  while (/^\.\.\//.test(url)) {
    url = url.substring(3);
    var idx = baseClean.lastIndexOf("/");
    if (idx === -1) break;
    baseClean = baseClean.substring(0, idx);
  }
  return baseClean + "/" + url;
}

/* \xe5\x90\x88\xe5\xb9\xb6\xe6\x89\x80\xe6\x9c\x89\xe5\x88\x86\xe7\x89\x87\xe5\xb9\xb6\xe8\xa7\xa6\xe5\x8f\x91\xe4\xb8\x8b\xe8\xbd\xbd */
'''

# Combine: before + clean code + after mergeAndSave
new_data = data[:comment_start] + clean_code + data[merge_pos:]

# Write as UTF-8 with BOM for maximum compatibility
bom = b'\xef\xbb\xbf'
with open(path, 'wb') as f:
    f.write(bom + new_data)

print(f"Done! Old size: {len(data)}, New size: {len(new_data) + 3}")
