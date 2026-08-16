# TikTok Downloader

A tiny local web app: paste a TikTok link → download the **HD video (no watermark)** or extract the **MP3**.

Frontend is one HTML page; the real work is done server-side by [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) + `ffmpeg`.

## Requirements

- Python 3.9+
- **ffmpeg** on your PATH (needed for MP3 extraction)
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: download from ffmpeg.org and add to PATH

## Setup & run

```bash
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

## How it works

- `POST /api/info` — returns title/thumbnail/uploader for the preview card.
- `GET  /api/download?type=video|mp3&url=…` — downloads with yt-dlp, converts if needed, streams the file back.

`bestvideo+bestaudio/best` pulls the clean (non-watermarked) stream when TikTok exposes it, falling back to the best single file otherwise.

## Keeping it working

TikTok changes its internals often. If downloads start failing, update the engine:

```bash
pip install -U yt-dlp
```

## Note

For your own content or material you have permission to use. Downloading others' videos may conflict with TikTok's Terms of Service and creators' rights.
