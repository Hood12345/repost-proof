from flask import Flask, request, send_file, jsonify
import os
import uuid
import subprocess
import traceback
import time
from utils.ffmpeg_mods import build_ffmpeg_command

app = Flask(__name__)
print("[DEBUG] Flask app initialized")

UPLOAD_DIR = "/tmp/repostproof"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def cleanup_tmp_folder():
    """Delete all files in the upload folder"""
    print("[CLEANUP] Cleaning up temporary folder...")
    for f in os.listdir(UPLOAD_DIR):
        try:
            os.remove(os.path.join(UPLOAD_DIR, f))
        except Exception as e:
            print(f"[CLEANUP ERROR] Could not delete {f}: {e}")
    print("[CLEANUP] Done.")

# Clean up any leftover files when the app starts
cleanup_tmp_folder()

@app.route("/repost-proof", methods=["POST"])
def repost_proof():
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
        # Clean up all old files after each run
        cleanup_tmp_folder()

@app.route("/file-download/<filename>")
def download_file(filename):
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    else:
        return "File not found", 404

print("[BOOT] App module loaded for Gunicorn")
print("[DEBUG] Flask app fully loaded")
