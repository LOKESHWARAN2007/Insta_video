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

## Notes & limits
- This app only handles **public** posts/reels. Private content needs cookie-based
  authentication, which isn't included here (added complexity + higher risk of violating
  Instagram's Terms of Service).
- Downloaded files are streamed to the browser and then deleted from the server —
  nothing is stored persistently.
- Free tiers on Render/Railway "sleep" after inactivity, so the first request after
  idling can take ~30 seconds to wake up.
- yt-dlp needs occasional updates as Instagram changes its site. Bump the version in
  `requirements.txt` (or run `pip install -U yt-dlp`) if downloads start failing.
- Respect copyright and Instagram's Terms of Service — only download content you have
  the right to download.
