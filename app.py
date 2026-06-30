"""
Téléchargeur Vidéo — backend Flask
"""

import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path

import yt_dlp
from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__)

BASE_DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "video_downloader_app"
BASE_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None

MAX_AGE_SECONDS = 60 * 30


def _cleanup_old_jobs() -> None:
    import time
    now = time.time()
    for child in BASE_DOWNLOAD_DIR.iterdir():
        try:
            if now - child.stat().st_mtime > MAX_AGE_SECONDS:
                shutil.rmtree(child, ignore_errors=True)
        except FileNotFoundError:
            pass


def _normalise_url(url: str) -> str:
    """Ajoute https:// si l'utilisateur a collé un lien sans scheme."""
    if not re.match(r"https?://", url, re.I):
        url = "https://" + url
    return url


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/download", methods=["POST"])
def api_download():
    _cleanup_old_jobs()

    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    audio_only = bool(data.get("audio_only"))

    if not url:
        return jsonify({"error": "Aucun lien fourni."}), 400

    url = _normalise_url(url)

    job_id = uuid.uuid4().hex
    job_dir = BASE_DOWNLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "outtmpl": str(job_dir / "%(title).150s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.0 Mobile/15E148 Safari/604.1"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    }

    if audio_only:
        ydl_opts["format"] = "bestaudio/best"
        if FFMPEG_AVAILABLE:
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
    else:
        if FFMPEG_AVAILABLE:
            ydl_opts["format"] = "bestvideo+bestaudio/best"
            ydl_opts["merge_output_format"] = "mp4"
        else:
            ydl_opts["format"] = "best"

    error_msg = None

    # Tentative 1 : extracteurs natifs yt-dlp (YouTube, Insta, TikTok…)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify({"error": f"Erreur inattendue : {e}"}), 500

    # Tentative 2 : extracteur générique (FIFA, ESPN, sites médias…)
    if error_msg and not any(f.is_file() for f in job_dir.iterdir()):
        generic_opts = dict(ydl_opts)
        generic_opts["force_generic_extractor"] = True
        try:
            with yt_dlp.YoutubeDL(generic_opts) as ydl:
                ydl.extract_info(url, download=True)
            error_msg = None
        except yt_dlp.utils.DownloadError as e2:
            error_msg = error_msg or str(e2)
        except Exception as e2:
            shutil.rmtree(job_dir, ignore_errors=True)
            return jsonify({"error": f"Erreur inattendue : {e2}"}), 500

    produced = [f for f in job_dir.iterdir() if f.is_file()]

    if not produced:
        shutil.rmtree(job_dir, ignore_errors=True)
        msg = error_msg or "Aucun fichier produit. Ce lien n'est peut-être pas une vidéo publique."
        msg = re.sub(r"\x1b\[[0-9;]*m", "", msg)
        return jsonify({"error": msg}), 422

    result_file = produced[0]
    response = send_file(
        str(result_file),
        as_attachment=True,
        download_name=result_file.name,
    )
    response.headers["X-Ffmpeg-Available"] = "1" if FFMPEG_AVAILABLE else "0"

    @response.call_on_close
    def _cleanup() -> None:
        shutil.rmtree(job_dir, ignore_errors=True)

    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
