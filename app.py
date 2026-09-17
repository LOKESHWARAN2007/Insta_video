import os
import glob
import shutil
import tempfile
import uuid
from datetime import datetime

from flask import Flask, request, render_template_string, send_file, jsonify
import yt_dlp
import imageio_ffmpeg

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# A static, bundled ffmpeg binary -- means we don't depend on the host
# having ffmpeg installed at the system level (Render/Railway etc. often
# don't, by default).
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

PLATFORM_NAMES = {
    "Instagram": "Instagram",
    "Youtube": "YouTube",
    "YoutubeShorts": "YouTube",
    "YoutubeTab": "YouTube",
}


def friendly_platform(extractor_key: str) -> str:
    return PLATFORM_NAMES.get(extractor_key, extractor_key or "Video")


def best_thumbnail(info: dict) -> str | None:
    if info.get("thumbnail"):
        return info["thumbnail"]
    thumbs = info.get("thumbnails") or []
    if thumbs:
        return thumbs[-1].get("url")
    return None


PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reelfetch — Video &amp; Audio Downloader</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0b0c12;
    --surface: rgba(27, 29, 40, 0.72);
    --surface-solid: #1b1d28;
    --border: rgba(255, 255, 255, 0.09);
    --border-strong: rgba(232, 181, 77, 0.45);
    --gold: #e8b54d;
    --gold-soft: #f0c165;
    --ig: #d84a8c;
    --yt: #e5484d;
    --text: #f1efe9;
    --text-muted: #93949f;
    --text-faint: #5c5e6b;
  }

  * { box-sizing: border-box; }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.001ms !important; transition-duration: 0.001ms !important; }
  }

  html, body {
    margin: 0;
    min-height: 100vh;
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', system-ui, sans-serif;
  }

  body {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 64px 28px;
    overflow-x: hidden;
  }

  /* ---- animated aurora backdrop: one bold, deliberate motion ---- */
  .aurora { position: fixed; inset: 0; z-index: 0; overflow: hidden; }
  .aurora span {
    position: absolute;
    width: 52vw;
    height: 52vw;
    border-radius: 50%;
    filter: blur(10px);
    opacity: 0.34;
    mix-blend-mode: screen;
  }
  .aurora span:nth-child(1) {
    background: radial-gradient(circle, var(--ig), transparent 70%);
    top: -18%; left: -12%;
    animation: drift1 26s ease-in-out infinite;
  }
  .aurora span:nth-child(2) {
    background: radial-gradient(circle, var(--yt), transparent 70%);
    bottom: -20%; right: -10%;
    animation: drift2 32s ease-in-out infinite;
  }
  .aurora span:nth-child(3) {
    background: radial-gradient(circle, var(--gold), transparent 72%);
    top: 30%; right: 18%;
    animation: drift3 22s ease-in-out infinite;
  }

  @keyframes drift1 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50% { transform: translate(6vw, 8vh) scale(1.12); }
  }
  @keyframes drift2 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50% { transform: translate(-7vw, -6vh) scale(1.1); }
  }
  @keyframes drift3 {
    0%, 100% { transform: translate(0, 0) scale(0.9); }
    50% { transform: translate(-4vw, 5vh) scale(1.05); }
  }

  /* film-strip rails, quieted to sit under the aurora */
  .rail { position: fixed; top: 0; bottom: 0; width: 22px; z-index: 1;
    background-color: rgba(13, 14, 19, 0.65);
    background-image: radial-gradient(circle, rgba(255,255,255,0.06) 3.2px, transparent 3.3px);
    background-size: 100% 32px;
    background-position: center 8px;
  }
  .rail.left { left: 0; }
  .rail.right { right: 0; }

  main {
    position: relative;
    z-index: 2;
    width: 100%;
    max-width: 480px;
    animation: rise 0.5s cubic-bezier(.2,.8,.2,1) both;
  }

  @keyframes rise {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 36px 32px;
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    box-shadow: 0 30px 60px -20px rgba(0,0,0,0.6);
  }

  .eyebrow-row { display: flex; align-items: center; gap: 8px; margin-bottom: 18px; }

  .rec-dot {
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--yt);
    box-shadow: 0 0 0 0 rgba(229, 72, 77, 0.6);
    animation: pulse 2.2s ease-in-out infinite;
  }
  @keyframes pulse {
    0%   { box-shadow: 0 0 0 0 rgba(229, 72, 77, 0.55); }
    70%  { box-shadow: 0 0 0 8px rgba(229, 72, 77, 0); }
    100% { box-shadow: 0 0 0 0 rgba(229, 72, 77, 0); }
  }

  .eyebrow { font-size: 0.8rem; color: var(--text-muted); letter-spacing: 0.02em; }

  h1 {
    font-family: 'Fraunces', serif;
    font-optical-sizing: auto;
    font-weight: 600;
    font-size: clamp(1.9rem, 5vw, 2.35rem);
    line-height: 1.14;
    margin: 0 0 12px;
  }
  h1 em { font-style: italic; color: var(--gold); }

  p.lede { color: var(--text-muted); font-size: 0.97rem; line-height: 1.55; margin: 0 0 28px; max-width: 42ch; }

  .platform-pills { display: flex; gap: 8px; margin-bottom: 24px; }
  .pill {
    font-size: 0.74rem; font-weight: 600; letter-spacing: 0.01em;
    padding: 5px 11px; border-radius: 999px; border: 1px solid var(--border);
    color: var(--text-muted);
  }
  .pill.ig { color: var(--ig); border-color: rgba(216, 74, 140, 0.35); }
  .pill.yt { color: var(--yt); border-color: rgba(229, 72, 77, 0.35); }

  form { display: flex; flex-direction: column; gap: 12px; }

  .field {
    display: flex; gap: 8px;
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border);
    border-radius: 12px; padding: 6px;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }
  .field:focus-within { border-color: var(--border-strong); box-shadow: 0 0 0 3px rgba(232, 181, 77, 0.12); }

  input[type=url] {
    flex: 1; min-width: 0; background: transparent; border: none; outline: none;
    color: var(--text); font-family: 'Inter', sans-serif; font-size: 0.95rem; padding: 12px 10px;
  }
  input[type=url]::placeholder { color: var(--text-faint); }

  button {
    position: relative; display: flex; align-items: center; justify-content: center; gap: 8px;
    border: none; border-radius: 8px; font-family: 'Inter', sans-serif; font-weight: 600;
    font-size: 0.92rem; cursor: pointer; transition: background 0.15s ease, transform 0.1s ease, opacity 0.15s ease;
    white-space: nowrap;
  }
  button:active:not(:disabled) { transform: scale(0.98); }
  button:disabled { cursor: default; opacity: 0.75; }

  .btn-primary { background: var(--gold); color: #201705; padding: 0 20px; }
  .btn-primary:hover:not(:disabled) { background: var(--gold-soft); }

  .btn-ghost {
    background: transparent; color: var(--text-muted); border: 1px solid var(--border);
    padding: 10px 16px; font-size: 0.85rem;
  }
  .btn-ghost:hover:not(:disabled) { color: var(--text); border-color: rgba(255,255,255,0.22); }

  .spinner {
    width: 15px; height: 15px; border-radius: 50%;
    border: 2px solid rgba(0,0,0,0.25); border-top-color: currentColor;
    display: none; animation: spin 0.7s linear infinite;
  }
  .btn-ghost .spinner { border-color: rgba(255,255,255,0.18); border-top-color: var(--text); }
  .loading .spinner { display: inline-block; }
  .loading .btn-label { display: none; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ---- preview card ---- */
  #preview { margin-top: 20px; display: none; }
  #preview.show { display: block; animation: fade-in 0.3s ease; }

  @keyframes fade-in { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }

  .preview-inner {
    display: flex; gap: 14px; padding: 14px;
    background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius: 14px;
  }

  .thumb-wrap {
    width: 96px; height: 96px; border-radius: 10px; overflow: hidden; flex-shrink: 0;
    background: linear-gradient(120deg, #23252f 25%, #2c2e3a 37%, #23252f 63%);
    background-size: 400% 100%;
  }
  .thumb-wrap.skeleton { animation: shimmer 1.4s ease infinite; }
  @keyframes shimmer { 0% { background-position: 100% 0; } 100% { background-position: 0 0; } }
  .thumb-wrap img { width: 100%; height: 100%; object-fit: cover; display: block; }

  .preview-meta { min-width: 0; display: flex; flex-direction: column; justify-content: center; gap: 6px; }
  .preview-title {
    font-size: 0.92rem; font-weight: 600; line-height: 1.35;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  }
  .preview-sub { font-size: 0.78rem; color: var(--text-muted); display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .skel-line { height: 10px; border-radius: 5px; background: rgba(255,255,255,0.08); }
  .skel-line.w1 { width: 80%; margin-bottom: 6px; }
  .skel-line.w2 { width: 45%; }

  .action-row { display: flex; gap: 10px; margin-top: 16px; }
  .action-row .btn-primary { flex: 1; }

  .status {
    margin-top: 16px; padding: 12px 15px; border-radius: 10px; font-size: 0.86rem; line-height: 1.5;
    display: none; animation: fade-in 0.25s ease;
  }
  .status.show { display: block; }
  .status.error { background: rgba(229, 72, 77, 0.1); border: 1px solid rgba(229, 72, 77, 0.3); color: #f3b5b7; }
  .status.success { background: rgba(232, 181, 77, 0.1); border: 1px solid rgba(232, 181, 77, 0.3); color: var(--gold); }

  .note {
    color: var(--text-faint); font-size: 0.76rem; line-height: 1.6;
    margin-top: 28px; border-top: 1px solid var(--border); padding-top: 18px;
  }

  .copyright {
    color: var(--text-faint); font-size: 0.72rem; letter-spacing: 0.01em;
    margin: 14px 0 0; text-align: center;
  }

  /* ---- MP3 dialog ---- */
  dialog#mp3-dialog {
    border: 1px solid var(--border); border-radius: 18px; padding: 0;
    background: var(--surface-solid); color: var(--text);
    width: min(420px, 90vw);
    box-shadow: 0 30px 70px -20px rgba(0,0,0,0.7);
  }
  dialog#mp3-dialog::backdrop { background: rgba(6, 6, 10, 0.68); backdrop-filter: blur(2px); }
  .dialog-inner { padding: 28px; }
  .dialog-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
  .dialog-head h2 { font-family: 'Fraunces', serif; font-size: 1.25rem; font-weight: 600; margin: 0; }
  .dialog-close {
    background: transparent; border: none; color: var(--text-muted); font-size: 1.1rem;
    width: 28px; height: 28px; border-radius: 50%; padding: 0; cursor: pointer;
  }
  .dialog-close:hover { color: var(--text); background: rgba(255,255,255,0.06); }
  #mp3-preview { display: flex; gap: 12px; align-items: center; margin-bottom: 20px; }
  #mp3-preview .thumb-wrap { width: 56px; height: 56px; }
  #mp3-preview .preview-title { font-size: 0.85rem; -webkit-line-clamp: 2; }
  .btn-convert { width: 100%; background: var(--gold); color: #201705; padding: 13px; font-size: 0.94rem; }
  .btn-convert:hover:not(:disabled) { background: var(--gold-soft); }

  @media (max-width: 520px) {
    body { padding: 40px 18px; }
    .rail { width: 14px; background-size: 100% 24px; }
    .card { padding: 28px 22px; }
    .field { flex-direction: column; }
    .action-row { flex-direction: column; }
  }
</style>
</head>
<body>
  <div class="aurora"><span></span><span></span><span></span></div>
  <div class="rail left"></div>
  <div class="rail right"></div>

  <main>
    <div class="card">
      <div class="eyebrow-row">
        <span class="rec-dot"></span>
        <span class="eyebrow">reelfetch</span>
      </div>

      <h1>Paste a link.<br>Press play on the <em>download</em>.</h1>
      <p class="lede">Grab a public Instagram reel or YouTube video, preview it first, then save the video or pull just the audio as MP3.</p>

      <div class="platform-pills">
        <span class="pill ig">Instagram</span>
        <span class="pill yt">YouTube</span>
      </div>

      <form id="dl-form">
        <div class="field">
          <input type="url" id="url" name="url" placeholder="Paste an Instagram or YouTube link..." required>
        </div>
      </form>

      <div id="preview">
        <div class="preview-inner">
          <div class="thumb-wrap" id="thumb-wrap"><img id="thumb-img" alt="" style="display:none;"></div>
          <div class="preview-meta" id="preview-meta">
            <div class="skel-line w1"></div>
            <div class="skel-line w2"></div>
          </div>
        </div>

        <div class="action-row">
          <button type="button" class="btn-primary" id="dl-btn">
            <span class="spinner"></span>
            <span class="btn-label">Download video</span>
          </button>
          <button type="button" class="btn-ghost" id="mp3-open-btn">
            <span class="btn-label">Convert to MP3</span>
          </button>
        </div>
      </div>

      <div class="status" id="status"></div>

      <p class="note">Only download content you have the right to. Private posts and age-restricted
      videos need a signed-in session, which this version doesn't support. Respect copyright when
      converting music or video to MP3.</p>

      <p class="copyright">&copy; {{ current_year }} loki_varient_01</p>
    </div>
  </main>

  <dialog id="mp3-dialog">
    <div class="dialog-inner">
      <div class="dialog-head">
        <h2>Convert to MP3</h2>
        <button type="button" class="dialog-close" id="mp3-close-btn">&times;</button>
      </div>
      <div id="mp3-preview">
        <div class="thumb-wrap"><img id="mp3-thumb-img" alt="" style="width:100%;height:100%;object-fit:cover;"></div>
        <div class="preview-title" id="mp3-title"></div>
      </div>
      <button type="button" class="btn-convert" id="mp3-convert-btn">
        <span class="spinner"></span>
        <span class="btn-label">Convert &amp; download</span>
      </button>
      <div class="status" id="mp3-status"></div>
    </div>
  </dialog>

<script>
  const urlInput = document.getElementById('url');
  const previewEl = document.getElementById('preview');
  const thumbWrap = document.getElementById('thumb-wrap');
  const thumbImg = document.getElementById('thumb-img');
  const previewMeta = document.getElementById('preview-meta');
  const statusEl = document.getElementById('status');
  const dlBtn = document.getElementById('dl-btn');

  const dialog = document.getElementById('mp3-dialog');
  const mp3OpenBtn = document.getElementById('mp3-open-btn');
  const mp3CloseBtn = document.getElementById('mp3-close-btn');
  const mp3ConvertBtn = document.getElementById('mp3-convert-btn');
  const mp3Status = document.getElementById('mp3-status');
  const mp3Thumb = document.getElementById('mp3-thumb-img');
  const mp3Title = document.getElementById('mp3-title');

  let currentInfo = null;
  let debounceTimer = null;

  function showStatus(el, kind, message) {
    el.textContent = message;
    el.className = 'status show ' + kind;
  }
  function hideStatus(el) { el.className = 'status'; }

  function secondsToClock(s) {
    if (!s && s !== 0) return '';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60).toString().padStart(2, '0');
    return m + ':' + sec;
  }

  function renderSkeleton() {
    previewEl.classList.add('show');
    thumbWrap.classList.add('skeleton');
    thumbImg.style.display = 'none';
    previewMeta.innerHTML = '<div class="skel-line w1"></div><div class="skel-line w2"></div>';
  }

  function renderPreview(info) {
    thumbWrap.classList.remove('skeleton');
    if (info.thumbnail) {
      thumbImg.src = info.thumbnail;
      thumbImg.style.display = 'block';
    } else {
      thumbImg.style.display = 'none';
    }
    const bits = [];
    if (info.platform) bits.push(info.platform);
    if (info.duration !== null && info.duration !== undefined) bits.push(secondsToClock(info.duration));
    if (info.uploader) bits.push(info.uploader);
    previewMeta.innerHTML =
      '<div class="preview-title">' + (info.title || 'Untitled') + '</div>' +
      '<div class="preview-sub">' + bits.map(b => '<span>' + b + '</span>').join('<span>·</span>') + '</div>';
  }

  async function fetchPreview(url) {
    renderSkeleton();
    try {
      const res = await fetch('/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'url=' + encodeURIComponent(url)
      });
      if (!res.ok) {
        previewEl.classList.remove('show');
        currentInfo = null;
        return;
      }
      const info = await res.json();
      currentInfo = info;
      renderPreview(info);
    } catch (err) {
      previewEl.classList.remove('show');
      currentInfo = null;
    }
  }

  urlInput.addEventListener('input', () => {
    hideStatus(statusEl);
    clearTimeout(debounceTimer);
    const val = urlInput.value.trim();
    if (!val.startsWith('http')) {
      previewEl.classList.remove('show');
      currentInfo = null;
      return;
    }
    debounceTimer = setTimeout(() => fetchPreview(val), 650);
  });

  async function downloadFile(endpoint, url, btn, statusTarget, defaultName) {
    btn.classList.add('loading');
    btn.disabled = true;
    hideStatus(statusTarget);
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'url=' + encodeURIComponent(url)
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: 'Something went wrong.' }));
        showStatus(statusTarget, 'error', data.error || 'Something went wrong.');
        return;
      }
      const disposition = res.headers.get('Content-Disposition') || '';
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match ? match[1] : defaultName;

      const blob = await res.blob();
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();

      showStatus(statusTarget, 'success', 'Saved: ' + filename);
    } catch (err) {
      showStatus(statusTarget, 'error', "Couldn't reach the server. Try again in a moment.");
    } finally {
      btn.classList.remove('loading');
      btn.disabled = false;
    }
  }

  dlBtn.addEventListener('click', () => {
    const val = urlInput.value.trim();
    if (!val) { showStatus(statusEl, 'error', 'Paste a URL first.'); return; }
    downloadFile('/download', val, dlBtn, statusEl, 'video.mp4');
  });

  mp3OpenBtn.addEventListener('click', () => {
    const val = urlInput.value.trim();
    if (!val) { showStatus(statusEl, 'error', 'Paste a URL first.'); return; }
    hideStatus(mp3Status);
    if (currentInfo) {
      mp3Title.textContent = currentInfo.title || 'Untitled';
      mp3Thumb.src = currentInfo.thumbnail || '';
    } else {
      mp3Title.textContent = 'Ready to convert';
      mp3Thumb.src = '';
    }
    dialog.showModal();
  });

  mp3CloseBtn.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.close(); });

  mp3ConvertBtn.addEventListener('click', () => {
    const val = urlInput.value.trim();
    if (!val) return;
    downloadFile('/convert', val, mp3ConvertBtn, mp3Status, 'audio.mp3');
  });
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE, current_year=datetime.now().year)


@app.route("/preview", methods=["POST"])
def preview():
    url = request.form.get("url", "").strip()
    if not url:
        return jsonify({"error": "Paste a URL first."}), 400

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            "title": info.get("title"),
            "thumbnail": best_thumbnail(info),
            "duration": info.get("duration"),
            "uploader": info.get("uploader") or info.get("channel"),
            "platform": friendly_platform(info.get("extractor_key")),
        })
    except Exception:
        return jsonify({"error": "Couldn't load a preview for that link."}), 422


@app.route("/download", methods=["POST"])
def download():
    url = request.form.get("url", "").strip()
    if not url:
        return jsonify({"error": "Paste a URL first."}), 400

    job_dir = tempfile.mkdtemp(prefix=f"igdl_{uuid.uuid4().hex}_")
    ydl_opts = {
        "outtmpl": os.path.join(job_dir, "%(title).100s.%(ext)s"),
        "format": "best",
        "quiet": True,
        "noplaylist": True,
        "ffmpeg_location": FFMPEG_PATH,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = glob.glob(os.path.join(job_dir, "*"))
        if not files:
            shutil.rmtree(job_dir, ignore_errors=True)
            return jsonify({"error": "Couldn't find a video at that link. It may be private."}), 422

        filepath = files[0]
        filename = os.path.basename(filepath)

        response = send_file(filepath, as_attachment=True, download_name=filename)
        response.call_on_close(lambda: shutil.rmtree(job_dir, ignore_errors=True))
        return response

    except yt_dlp.utils.DownloadError:
        shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify({"error": "That link couldn't be fetched. Check it's public and try again."}), 422
    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify({"error": "Something went wrong on our end. Try again shortly."}), 500


@app.route("/convert", methods=["POST"])
def convert():
    url = request.form.get("url", "").strip()
    if not url:
        return jsonify({"error": "Paste a URL first."}), 400

    job_dir = tempfile.mkdtemp(prefix=f"igmp3_{uuid.uuid4().hex}_")
    ydl_opts = {
        "outtmpl": os.path.join(job_dir, "%(title).100s.%(ext)s"),
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "ffmpeg_location": FFMPEG_PATH,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = glob.glob(os.path.join(job_dir, "*.mp3"))
        if not files:
            shutil.rmtree(job_dir, ignore_errors=True)
            return jsonify({"error": "Couldn't convert that link to MP3."}), 422

        filepath = files[0]
        filename = os.path.basename(filepath)

        response = send_file(filepath, as_attachment=True, download_name=filename)
        response.call_on_close(lambda: shutil.rmtree(job_dir, ignore_errors=True))
        return response

    except yt_dlp.utils.DownloadError:
        shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify({"error": "That link couldn't be converted. Check it's public and try again."}), 422
    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify({"error": "Something went wrong during conversion. Try again shortly."}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
