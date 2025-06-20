from flask import Flask, request, send_file, jsonify
import os
import uuid
import subprocess
import traceback
import time
from datetime import datetime, timedelta
from utils.ffmpeg_mods import build_ffmpeg_command

app = Flask(__name__)

UPLOAD_DIR = "/tmp/repostproof"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def clean_old_files(directory, max_age_minutes=60):
    now = time.time()
    deleted_files = 0
    for filename in os.listdir(directory):
        path = os.path.join(directory, filename)
        if os.path.isfile(path):
            file_age_minutes = (now - os.path.getmtime(path)) / 60
            if file_age_minutes > max_age_minutes:
                try:
                    os.remove(path)
                    deleted_files += 1
                except Exception as e:
                    print(f"[CLEANUP ERROR] Couldn't delete {path}: {e}")
    if deleted_files:
        print(f"[CLEANUP] Deleted {deleted_files} old files from {directory}")

@app.route("/repost-proof", methods=["POST"])
def repost_proof():
    clean_old_files(UPLOAD_DIR)  # Cleanup before processing

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    video = request.files['file']
    filename = f"{uuid.uuid4()}.mp4"
    input_path = os.path.join(UPLOAD_DIR, f"in_{filename}")
    output_path = os.path.join(UPLOAD_DIR, f"out_{filename}")

    try:
        video.save(input_path)
        print(f"[INFO] File saved to {input_path}")

        ffmpeg_cmd, pitch_preserved = build_ffmpeg_command(input_path, output_path)
        print("[DEBUG] Running FFmpeg command:")
        print(" ".join(ffmpeg_cmd))

        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("[ERROR] FFmpeg stderr:")
            print(result.stderr)
            raise RuntimeError(result.stderr.strip())

        size = os.path.getsize(output_path)
        file_too_large = size > 50 * 1024 * 1024

        result_json = {
            "success": True,
            "file_size_MB": round(size / (1024 * 1024), 2),
            "pitch_preserved": pitch_preserved,
            "ffmpeg_cmd": " ".join(ffmpeg_cmd)
        }

        if file_too_large:
            public_link = f"https://repost-proof-production.up.railway.app/file-download/{os.path.basename(output_path)}"
            result_json["url"] = public_link
            return jsonify(result_json)
        else:
            download_name = f"hco_{int(time.time())}.mp4"
            return send_file(output_path, as_attachment=True, download_name=download_name)

    except Exception as e:
        print("[EXCEPTION] Something went wrong during processing:")
        print(traceback.format_exc())
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500
    finally:
        try:
            os.remove(input_path)
        except:
            pass

@app.route("/file-download/<filename>")
def download_file(filename):
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    else:
        return "File not found", 404

if __name__ == "__main__":
    clean_old_files(UPLOAD_DIR)  # Clean existing leftover files at startup
    print("[BOOT] App module loaded for Gunicorn")
