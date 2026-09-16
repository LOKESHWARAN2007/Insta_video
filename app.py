import os
import glob
import shutil
import tempfile
import uuid

from flask import Flask, request, render_template_string, send_file, jsonify
import yt_dlp

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reelfetch — Instagram Video Downloader</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #121319;
    --surface: #1b1d28;
    --surface-2: #23252f;
    --rail: #0d0e13;
    --hole: #33333d;
    --gold: #e8b54d;
    --gold-dim: #a97f2f;
    --red: #e5484d;
    --text: #ece9e2;
    --text-muted: #8b8d98;
    --border: #313340;
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
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 64px 56px;
  }

  /* film-strip rails down each side of the viewport */
  body::before, body::after {
    content: "";
    position: fixed;
    top: 0; bottom: 0;
    width: 28px;
    background-color: var(--rail);
    background-image: radial-gradient(circle, var(--hole) 3.5px, transparent 3.6px);
    background-size: 100% 34px;
    background-position: center 8px;
  }
  body::before { left: 0; }
  body::after { right: 0; }

  main {
    width: 100%;
    max-width: 460px;
  }

  .eyebrow-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 18px;
  }

  .rec-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--red);
    box-shadow: 0 0 0 0 rgba(229, 72, 77, 0.6);
    animation: pulse 2.2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%   { box-shadow: 0 0 0 0 rgba(229, 72, 77, 0.55); }
    70%  { box-shadow: 0 0 0 8px rgba(229, 72, 77, 0); }
    100% { box-shadow: 0 0 0 0 rgba(229, 72, 77, 0); }
  }

  .eyebrow {
    font-size: 0.8rem;
    color: var(--text-muted);
    letter-spacing: 0.02em;
  }

  h1 {
    font-family: 'Fraunces', serif;
    font-optical-sizing: auto;
    font-weight: 600;
    font-size: clamp(2rem, 5vw, 2.6rem);
    line-height: 1.12;
    margin: 0 0 14px;
    color: var(--text);
  }

  h1 em {
    font-style: italic;
    color: var(--gold);
  }

  p.lede {
    color: var(--text-muted);
    font-size: 1rem;
    line-height: 1.55;
    margin: 0 0 36px;
    max-width: 40ch;
  }

  form {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .field {
    display: flex;
    gap: 8px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 6px;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .field:focus-within {
    border-color: var(--gold-dim);
    box-shadow: 0 0 0 3px rgba(232, 181, 77, 0.14);
  }

  input[type=url] {
    flex: 1;
    min-width: 0;
    background: transparent;
    border: none;
    outline: none;
    color: var(--text);
    font-family: 'Inter', sans-serif;
    font-size: 0.95rem;
    padding: 12px 10px;
  }

  input[type=url]::placeholder { color: #5c5e6b; }

  button {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    border: none;
    border-radius: 8px;
    background: var(--gold);
    color: #201705;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.95rem;
    padding: 0 22px;
    cursor: pointer;
    transition: background 0.15s ease, transform 0.1s ease;
    white-space: nowrap;
  }

  button:hover:not(:disabled) { background: #f0c165; }
  button:active:not(:disabled) { transform: scale(0.98); }
  button:disabled { cursor: default; opacity: 0.85; }

  .reel {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    border: 2px solid rgba(32, 23, 5, 0.3);
    border-top-color: #201705;
    display: none;
    animation: spin 0.7s linear infinite;
  }

  button.loading .reel { display: inline-block; }
  button.loading .btn-label { display: none; }

  @keyframes spin { to { transform: rotate(360deg); } }

  .status {
    margin-top: 18px;
    padding: 13px 16px;
    border-radius: 10px;
    font-size: 0.88rem;
    line-height: 1.5;
    display: none;
    animation: fade-in 0.25s ease;
  }

  .status.show { display: block; }
  .status.error { background: rgba(229, 72, 77, 0.1); border: 1px solid rgba(229, 72, 77, 0.3); color: #f3b5b7; }
  .status.success { background: rgba(232, 181, 77, 0.1); border: 1px solid rgba(232, 181, 77, 0.3); color: var(--gold); }

  @keyframes fade-in {
    from { opacity: 0; transform: translateY(-4px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .note {
    color: #5c5e6b;
    font-size: 0.78rem;
    line-height: 1.6;
    margin-top: 40px;
    border-top: 1px solid var(--border);
    padding-top: 20px;
  }

  @media (max-width: 520px) {
    body { padding: 40px 40px; }
    body::before, body::after { width: 18px; background-size: 100% 26px; }
    .field { flex-direction: column; }
    button { padding: 12px 22px; }
  }
</style>
</head>
<body>
<main>
  <div class="eyebrow-row">
    <span class="rec-dot"></span>
    <span class="eyebrow">reelfetch</span>
  </div>

  <h1>Paste a link.<br>Press play on the <em>download</em>.</h1>
  <p class="lede">Drop in a public Instagram reel or post URL and it lands in your downloads — nothing kept, nothing stored.</p>

  <form id="dl-form">
    <div class="field">
      <input type="url" id="url" name="url" placeholder="https://www.instagram.com/reel/..." required>
      <button type="submit" id="dl-btn">
        <span class="reel"></span>
        <span class="btn-label">Download</span>
      </button>
    </div>
  </form>

  <div class="status" id="status"></div>

  <p class="note">Only download content you have the right to. Private posts need a signed-in
  session, which this version doesn't support.</p>
</main>

<script>
  const form = document.getElementById('dl-form');
  const btn = document.getElementById('dl-btn');
  const urlInput = document.getElementById('url');
  const statusEl = document.getElementById('status');

  function showStatus(kind, message) {
    statusEl.textContent = message;
    statusEl.className = 'status show ' + kind;
  }

  function hideStatus() {
    statusEl.className = 'status';
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideStatus();
    btn.classList.add('loading');
    btn.disabled = true;

    try {
      const res = await fetch('/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'url=' + encodeURIComponent(urlInput.value.trim())
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: 'Something went wrong.' }));
        showStatus('error', data.error || 'Something went wrong.');
        return;
      }

      const disposition = res.headers.get('Content-Disposition') || '';
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match ? match[1] : 'video.mp4';

      const blob = await res.blob();
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();

      showStatus('success', 'Saved: ' + filename);
      urlInput.value = '';
    } catch (err) {
      showStatus('error', 'Couldn\\'t reach the server. Try again in a moment.');
    } finally {
      btn.classList.remove('loading');
      btn.disabled = false;
    }
  });
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
