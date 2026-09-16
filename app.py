import os
import glob
import shutil
import tempfile
import uuid

from flask import Flask, request, render_template_string, send_file, flash, redirect, url_for
import yt_dlp

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Instagram Video Downloader</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 560px; margin: 60px auto; padding: 0 20px; color: #222; }
    h1 { font-size: 1.4rem; }
    form { display: flex; gap: 8px; margin-top: 20px; }
    input[type=url] { flex: 1; padding: 10px; font-size: 1rem; border: 1px solid #ccc; border-radius: 6px; }
    button { padding: 10px 18px; font-size: 1rem; border: none; border-radius: 6px; background: #222; color: #fff; cursor: pointer; }
    button:hover { background: #444; }
    .flash { background: #fee; border: 1px solid #f99; padding: 10px; border-radius: 6px; margin-top: 16px; }
    .note { color: #666; font-size: 0.85rem; margin-top: 24px; }
  </style>
</head>
<body>
  <h1>Instagram Video Downloader</h1>
  <p>Paste a public Instagram post/reel URL below.</p>
  <form method="post" action="/download">
    <input type="url" name="url" placeholder="https://www.instagram.com/reel/..." required>
    <button type="submit">Download</button>
  </form>
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      {% for m in messages %}<div class="flash">{{ m }}</div>{% endfor %}
    {% endif %}
  {% endwith %}
  <p class="note">Only download content you have the right to download. Private posts require
  session cookies, which this simple version does not support.</p>
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
        flash("Please enter a URL.")
        return redirect(url_for("index"))

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
            flash("No file was downloaded. The link may be private or invalid.")
            return redirect(url_for("index"))

        filepath = files[0]
        filename = os.path.basename(filepath)

        # send_file streams the file; clean up the temp dir afterwards
        response = send_file(filepath, as_attachment=True, download_name=filename)
        response.call_on_close(lambda: shutil.rmtree(job_dir, ignore_errors=True))
        return response

    except yt_dlp.utils.DownloadError as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        flash(f"Download failed: {e}")
        return redirect(url_for("index"))
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        flash(f"Something went wrong: {e}")
        return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
