"""
Téléchargeur Vidéo — backend Flask
-----------------------------------
Sert une page web (mobile-friendly) où on colle un lien YouTube / Instagram /
TikTok / Pinterest, et reçoit le fichier vidéo (ou audio) en retour.

Lancement local :
    python app.py
puis ouvrez http://<IP-de-votre-ordinateur>:5000 depuis votre téléphone
(sur le même Wi-Fi).

Déploiement : voir README.md.
"""

import os
import shutil
import tempfile
import uuid
from pathlib import Path

import yt_dlp
from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__)

BASE_DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "video_downloader_app"
BASE_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ffmpeg est nécessaire pour fusionner vidéo+audio en qualité max et pour
# convertir l'audio en mp3. S'il est absent, on bascule sur des formats qui
# n'ont pas besoin de fusion plutôt que de planter.
FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None

MAX_AGE_SECONDS = 60 * 30  # nettoyage de sécurité des vieux dossiers orphelins


def _cleanup_old_jobs() -> None:
    """Supprime les dossiers de téléchargement de plus de 30 min (au cas où
    un nettoyage normal aurait échoué, par ex. après un crash)."""
    import time

    now = time.time()
    for child in BASE_DOWNLOAD_DIR.iterdir():
        try:
            if now - child.stat().st_mtime > MAX_AGE_SECONDS:
                shutil.rmtree(child, ignore_errors=True)
        except FileNotFoundError:
            pass


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
    if not url.lower().startswith(("http://", "https://")):
        return jsonify({"error": "Ce n'est pas un lien valide."}), 400

    job_id = uuid.uuid4().hex
    job_dir = BASE_DOWNLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "outtmpl": str(job_dir / "%(title).150s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
    }

    if audio_only:
        ydl_opts["format"] = "bestaudio/best"
        if FFMPEG_AVAILABLE:
            # Convertit en mp3 (nécessite ffmpeg)
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        # Sans ffmpeg : on garde le fichier audio dans son format d'origine
        # (m4a/webm/opus) plutôt que de planter en voulant le convertir.
    else:
        if FFMPEG_AVAILABLE:
            # Fusionne la meilleure piste vidéo et la meilleure piste audio
            ydl_opts["format"] = "bestvideo+bestaudio/best"
            ydl_opts["merge_output_format"] = "mp4"
        else:
            # Sans ffmpeg, on ne peut pas fusionner deux flux séparés : on
            # prend directement le meilleur format déjà combiné (souvent un
            # peu moins défini sur YouTube, identique sur TikTok/Insta/Pinterest).
            ydl_opts["format"] = "best"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify({"error": f"Téléchargement impossible : {e}"}), 422
    except Exception as e:  # noqa: BLE001
        shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify({"error": f"Erreur inattendue : {e}"}), 500

    produced = [f for f in job_dir.iterdir() if f.is_file()]
    if not produced:
        shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify({"error": "Aucun fichier produit."}), 500

    result_file = produced[0]

    response = send_file(
        str(result_file),
        as_attachment=True,
        download_name=result_file.name,
    )
    response.headers["X-Ffmpeg-Available"] = "1" if FFMPEG_AVAILABLE else "0"

    # Nettoie le dossier temporaire une fois le fichier envoyé au téléphone.
    @response.call_on_close
    def _cleanup() -> None:
        shutil.rmtree(job_dir, ignore_errors=True)

    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # host="0.0.0.0" est nécessaire pour être accessible depuis le téléphone
    app.run(host="0.0.0.0", port=port, debug=False)
