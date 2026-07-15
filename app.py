import os
import uuid
import threading
import subprocess
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_from_directory, abort
import yt_dlp

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# In-memory job store (job_id -> status dict)
JOBS = {}


def clean_old_files(max_age_seconds=3600):
    """Purani downloaded files ko hata dete hain taaki disk full na ho."""
    now = datetime.now().timestamp()
    try:
        for f in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR, f)
            try:
                if now - os.path.getmtime(path) > max_age_seconds:
                    os.remove(path)
            except OSError:
                pass
    except FileNotFoundError:
        pass


def seconds_from_hms(hms):
    """'HH:MM:SS' ya 'MM:SS' string ko seconds me convert karta hai."""
    if not hms:
        return None
    hms = hms.strip()
    if not hms:
        return None
    try:
        parts = [int(p) for p in hms.split(":")]
    except ValueError:
        return None
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts[-3:]
    return h * 3600 + m * 60 + s


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def video_info():
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL missing hai"}), 400

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify({"error": "Video info nahi mil paayi. Link check karein."}), 400

    formats = info.get("formats", []) or []
    heights = sorted({f.get("height") for f in formats if f.get("height")}, reverse=True)
    available_qualities = [f"{h}p" for h in heights if h]

    result = {
        "id": info.get("id"),
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "duration_string": info.get("duration_string"),
        "uploader": info.get("uploader"),
        "available_qualities": available_qualities,
    }
    return jsonify(result)


QUALITY_MAP = {
    "auto": "bestvideo+bestaudio/best",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "1440p": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
    "4k": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
}


def run_job(job_id, url, start, end, quality, fmt):
    job = JOBS[job_id]
    downloaded_path = None
    try:
        job["status"] = "downloading"
        job["progress"] = 0

        out_template = os.path.join(DOWNLOAD_DIR, f"{job_id}_src.%(ext)s")
        audio_only = fmt in ("mp3", "m4a")

        def progress_hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                if total:
                    job["progress"] = min(90, int(downloaded / total * 85))
            elif d["status"] == "finished":
                job["progress"] = 90

        ydl_opts = {
            "outtmpl": out_template,
            "quiet": True,
            "noplaylist": True,
            "progress_hooks": [progress_hook],
        }

        if audio_only:
            ydl_opts["format"] = "bestaudio/best"
        else:
            ydl_opts["format"] = QUALITY_MAP.get(quality, QUALITY_MAP["auto"])
            ydl_opts["merge_output_format"] = "mp4"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        # actual downloaded filename dhoondo (ext yt-dlp decide karta hai)
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(f"{job_id}_src"):
                downloaded_path = os.path.join(DOWNLOAD_DIR, f)
                break

        if not downloaded_path:
            raise RuntimeError("Downloaded file nahi mili")

        job["status"] = "processing"
        job["progress"] = 92

        final_name = f"{job_id}_final.{fmt}"
        final_path = os.path.join(DOWNLOAD_DIR, final_name)

        start_sec = seconds_from_hms(start)
        end_sec = seconds_from_hms(end)

        ffmpeg_cmd = ["ffmpeg", "-y"]
        if start_sec is not None:
            ffmpeg_cmd += ["-ss", str(start_sec)]
        ffmpeg_cmd += ["-i", downloaded_path]
        if end_sec is not None and start_sec is not None and end_sec > start_sec:
            ffmpeg_cmd += ["-t", str(end_sec - start_sec)]
        elif end_sec is not None and start_sec is None:
            ffmpeg_cmd += ["-t", str(end_sec)]

        if fmt == "mp3":
            ffmpeg_cmd += ["-vn", "-acodec", "libmp3lame", "-q:a", "2"]
        elif fmt == "m4a":
            ffmpeg_cmd += ["-vn", "-acodec", "aac", "-b:a", "192k"]
        elif fmt == "mp4":
            ffmpeg_cmd += ["-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", "-preset", "fast"]
        elif fmt == "webm":
            ffmpeg_cmd += ["-c:v", "libvpx-vp9", "-c:a", "libopus"]

        ffmpeg_cmd.append(final_path)

        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

        job["status"] = "done"
        job["progress"] = 100
        job["file"] = final_name

    except subprocess.CalledProcessError:
        job["status"] = "error"
        job["error"] = "FFmpeg processing fail hui. Time range ya format check karein."
    except Exception as e:
        job["status"] = "error"
        job["error"] = f"Kuch galat ho gaya: {str(e)}"
    finally:
        if downloaded_path and os.path.exists(downloaded_path):
            try:
                os.remove(downloaded_path)
            except OSError:
                pass


@app.route("/api/start-download", methods=["POST"])
def start_download():
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get("url") or "").strip()
    start = (data.get("start") or "").strip()
    end = (data.get("end") or "").strip()
    quality = (data.get("quality") or "auto").strip()
    fmt = (data.get("format") or "mp4").strip()

    if not url:
        return jsonify({"error": "URL missing hai"}), 400
    if fmt not in ("mp4", "mp3", "m4a", "webm"):
        return jsonify({"error": "Format invalid hai"}), 400

    clean_old_files()

    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {"status": "queued", "progress": 0}

    thread = threading.Thread(
        target=run_job, args=(job_id, url, start, end, quality, fmt), daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/progress/<job_id>")
def progress(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job nahi mila"}), 404
    return jsonify(job)


@app.route("/api/download-file/<job_id>")
def download_file(job_id):
    job = JOBS.get(job_id)
    if not job or job.get("status") != "done":
        abort(404)
    return send_from_directory(DOWNLOAD_DIR, job["file"], as_attachment=True)


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
