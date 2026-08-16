"""
TikTok Downloader — Flask backend
=================================
Paste a TikTok link, get:
  • HD video without watermark  (yt-dlp pulls the clean "play" stream)
  • MP3 audio                   (extracted with ffmpeg)

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000

Requires ffmpeg on your PATH for MP3 extraction.
For your own / permitted content only — respect TikTok's Terms and creators' rights.
"""

import io
import os
import re
import shutil
import tempfile

from flask import (
    Flask, request, jsonify, render_template, send_file,
)
import yt_dlp

app = Flask(__name__)


def check_impersonation():
    """TikTok requires browser impersonation (curl_cffi). Warn loudly if missing."""
    try:
        import curl_cffi  # noqa: F401
        return True
    except ImportError:
        print('\n' + '=' * 68)
        print('  ⚠  curl_cffi is NOT installed — TikTok downloads WILL fail.')
        print('     TikTok needs browser impersonation to work.')
        print('     Fix it with:')
        print('         pip install -U "yt-dlp[default,curl-cffi]"')
        print('=' * 68 + '\n')
        return False


# Accept tiktok.com and the short-link hosts (vm./vt./m.)
TIKTOK_RE = re.compile(
    r'https?://(?:www\.|vm\.|vt\.|m\.)?tiktok\.com/', re.IGNORECASE
)


def is_valid_tiktok(url: str) -> bool:
    return bool(url and TIKTOK_RE.search(url.strip()))


def safe_name(title: str, fallback: str = 'tiktok') -> str:
    name = re.sub(r'[^\w\-]+', '_', title or '').strip('_')[:60]
    return name or fallback


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/info', methods=['POST'])
def info():
    """Return lightweight metadata for a preview (no download)."""
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    if not is_valid_tiktok(url):
        return jsonify({'error': 'Please paste a valid TikTok link.'}), 400
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
            meta = ydl.extract_info(url, download=False)
        return jsonify({
            'title': meta.get('title') or meta.get('description') or 'TikTok video',
            'uploader': meta.get('uploader') or meta.get('creator'),
            'thumbnail': meta.get('thumbnail'),
            'duration': meta.get('duration'),
        })
    except Exception as e:
        return jsonify({'error': f'Could not read that video: {e}'}), 502


@app.route('/api/download')
def download():
    """Download the video (no watermark) or extract MP3, stream it back."""
    url = request.args.get('url', '').strip()
    kind = request.args.get('type', 'video')  # 'video' or 'mp3'

    if not is_valid_tiktok(url):
        return jsonify({'error': 'Please paste a valid TikTok link.'}), 400

    tmpdir = tempfile.mkdtemp(prefix='ttdl_')
    outtmpl = os.path.join(tmpdir, '%(id)s.%(ext)s')

    if kind == 'mp3':
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': outtmpl,
            'quiet': True,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        # bestvideo+bestaudio prefers the clean (non-watermarked) stream;
        # falls back to a single 'best' progressive file when needed.
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': outtmpl,
            'quiet': True,
            'noplaylist': True,
            'merge_output_format': 'mp4',
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(url, download=True)

        # Locate the finished file (postprocessing changes the extension).
        result = None
        wanted_mp3 = (kind == 'mp3')
        for f in sorted(os.listdir(tmpdir)):
            if f.endswith('.part'):
                continue
            if wanted_mp3 and not f.endswith('.mp3'):
                continue
            full = os.path.join(tmpdir, f)
            if result is None or os.path.getsize(full) > os.path.getsize(result):
                result = full
        if not result:
            raise RuntimeError('Downloaded file not found after processing.')

        ext = 'mp3' if wanted_mp3 else (os.path.splitext(result)[1].lstrip('.') or 'mp4')
        mime = 'audio/mpeg' if wanted_mp3 else 'video/mp4'
        dl_name = f'{safe_name(meta.get("title") or meta.get("id"))}.{ext}'

        # Read into memory so we can delete the temp dir immediately
        # (TikTok clips are small — no streaming/cleanup race to worry about).
        with open(result, 'rb') as fh:
            buf = io.BytesIO(fh.read())
        buf.seek(0)
        return send_file(buf, as_attachment=True,
                         download_name=dl_name, mimetype=mime)

    except Exception as e:
        msg = str(e)
        if 'impersonat' in msg.lower():
            msg += ('  →  Fix: pip install -U "yt-dlp[default,curl-cffi]" '
                    'then restart the app.')
        return jsonify({'error': f'Download failed: {msg}'}), 502
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == '__main__':
    check_impersonation()
    app.run(host='127.0.0.1', port=5000, debug=True)
