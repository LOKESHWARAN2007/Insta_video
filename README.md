# Instagram Video Downloader — Deployment Guide

## Files
- `app.py` — Flask app (frontend + backend in one file)
- `requirements.txt` — Python dependencies
- `Procfile` — tells the host how to start the app

## 1. Run it locally first
```bash
pip install -r requirements.txt --break-system-packages
python app.py
```
Open http://localhost:5000 and test with a public Instagram reel/post URL.

## 2. Put it in a GitHub repo
```bash
git init
git add app.py requirements.txt Procfile README.md
git commit -m "Instagram downloader web app"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

## 3. Deploy (Render — free tier, easiest option)
1. Go to https://render.com and sign in with GitHub.
2. Click **New +** → **Web Service** → select your repo.
3. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** Free
4. Click **Create Web Service**. Render will build and deploy; you'll get a URL like
   `https://your-app.onrender.com`.

### Alternatives
- **Railway** (railway.app): similar flow, connect GitHub repo, auto-detects Procfile.
- **Fly.io**: `fly launch` in the project folder, follow prompts (needs `fly.toml`, which `fly launch` generates for you).
- **PythonAnywhere**: good for simple always-on hosting without Docker/buildpacks.

## What's included
- A live thumbnail/title preview once you paste a link (debounced, so it fetches
  shortly after you stop typing).
- Works with both **Instagram** (public reels/posts) and **YouTube** (public videos) —
  same `/download` endpoint handles both, since yt-dlp detects the site automatically.
- A **Convert to MP3** dialog that pulls audio-only and transcodes it with ffmpeg.

## About the MP3 conversion
Audio extraction needs ffmpeg. Rather than relying on the host having it installed at
the system level (Render's native Python runtime doesn't, by default), this app uses
the `imageio-ffmpeg` package, which bundles a static ffmpeg binary and points yt-dlp at
it directly — no extra buildpacks or Dockerfile needed. It does make the build a bit
larger and the first install slightly slower.

## Notes & limits
- This app only handles **public** content. Private posts and age-restricted videos need
  cookie-based authentication, which isn't included here.
- Downloaded files are streamed to the browser and then deleted from the server —
  nothing is stored persistently.
- Free tiers on Render/Railway "sleep" after inactivity, so the first request after
  idling can take ~30 seconds to wake up — and MP3 conversion is slower than a plain
  video download since it has to transcode.
- yt-dlp needs occasional updates as Instagram/YouTube change their sites. Bump the
  version in `requirements.txt` (or run `pip install -U yt-dlp`) if downloads start
  failing.
- Respect copyright and each platform's Terms of Service — only download or convert
  content you have the right to.
