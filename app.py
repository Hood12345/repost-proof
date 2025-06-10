from flask import Flask, request, send_file, jsonify
import os
import uuid
import subprocess
from utils.ffmpeg_mods import build_ffmpeg_command

app = Flask(__name__)

# Temp directory for input/output
UPLOAD_DIR = "/tmp/repostproof"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/repost-proof", methods=["POST"])
def repost_proof():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    video = request.files['file']
    filename = f"{uuid.uuid4()}.mp4"
    input_path = os.path.join(UPLOAD_DIR, f"in_{filename}")
    output_path = os.path.join(UPLOAD_DIR, f"out_{filename}")

    video.save(input_path)

    try:
        ffmpeg_cmd, pitch_preserved = build_ffmpeg_command(input_path, output_path)
        subprocess.run(ffmpeg_cmd, check=True)

        size = os.path.getsize(output_path)
        file_too_large = size > 50 * 1024 * 1024

        result = {
            "success": True,
            "file_size_MB": round(size / (1024 * 1024), 2),
            "pitch_preserved": pitch_preserved,
            "ffmpeg_cmd": " ".join(ffmpeg_cmd)
        }

        if file_too_large:
            public_link = f"https://yourdomain.com/file-download/{os.path.basename(output_path)}"
            result["url"] = public_link
            return jsonify(result)
        else:
            return send_file(output_path, as_attachment=True, download_name="repost_safe.mp4")

    except subprocess.CalledProcessError as e:
        return jsonify({"error": "FFmpeg failed", "details": str(e)}), 500
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

# ✅ This line is REQUIRED for Railway deployment
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
