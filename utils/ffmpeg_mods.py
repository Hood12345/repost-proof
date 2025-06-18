# utils/ffmpeg_mods.py
import os
import random
import subprocess

# --------------------------------------------------------------------------- helpers
def has_rubberband() -> bool:
    """Detect if ffmpeg was built with the rubberband filter (pitch preservation)."""
    try:
        output = subprocess.check_output(['ffmpeg', '-filters'], stderr=subprocess.DEVNULL)
        return b"rubberband" in output
    except Exception:
        return False


# --------------------------------------------------------------------------- main
def build_ffmpeg_command(input_path: str, output_path: str):
    """
    Build an ffmpeg command that:
      • applies subtle, randomized video & audio variations (defeats perceptual hashes)
      • keeps visual quality high (CRF 22–24, veryfast)
      • optionally preserves pitch if rubberband is available

    Returns (cmd_list, pitch_preserved_bool)
    """

    # ── general encode params ────────────────────────────────────────────────
    crf = random.choice([22, 23, 24])
    gop = random.choice([24, 48, 72])

    # ---------------------------------------------------------------- video filters
    # ① Random zoom-crop (1–3 %)   – breaks spatial pHash
    zoom  = round(random.uniform(1.015, 1.035), 3)

    # ② Optional ±3-frame time shift – kills frame-sequence hash
    frame_shift = random.randint(-3, 3)

    # ③ Low-gain noise (5–10) – destroys DCT hash, nearly invisible
    noise_strength = random.randint(5, 10)

    # ④ Micro colour & brightness jitter
    sat = round(random.uniform(0.99, 1.01), 3)
    bri = round(random.uniform(0.99, 1.01), 3)
    con = round(random.uniform(1.00, 1.03), 3)

    # ⑤ Your existing crop / pad / drawbox trick (kept)
    crop_pad = "crop=iw-2:ih-2,pad=iw+2:ih+2:1:1,drawbox=x=10:y=10:w=5:h=5:color=white@0.001:t=fill"

    vf_parts = [
        f"scale=iw*{zoom}:ih*{zoom},crop=iw/{zoom}:ih/{zoom}",
        f"setpts=PTS+{frame_shift}/TB" if frame_shift else "",
        crop_pad,
        f"noise=alls={noise_strength}:allf=t+u",
        f"eq=brightness={bri}:contrast={con}:saturation={sat}",
        "hue=s=1.01",                      # your previous hue tweak (unchanged)
        "unsharp=5:5:0.8:5:5:0.0",         # mild sharpen
        "deband"                           # clean banding
    ]
    vfilter = ",".join([p for p in vf_parts if p])

    # ---------------------------------------------------------------- audio filters
    tempo = round(random.uniform(0.987, 1.013), 3)    # ±1.3 % tempo
    audio_filters = [f"atempo={tempo}",
                     "equalizer=f=200:t=q:w=1:g=1",
                     "dcshift=0.01:0"]

    if has_rubberband():
        audio_filters.insert(0, f"rubberband=tempo={tempo}")
        pitch_preserved = True
    else:
        # simple resample keeps approx pitch but not perfect
        audio_filters.insert(1, f"asetrate=44100/{tempo},aresample=44100")
        pitch_preserved = False

    afilter = ",".join(audio_filters)

    # ---------------------------------------------------------------- command list
    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-i", input_path,
        "-vf", vfilter,
        "-af", afilter,
        "-map_metadata", "-1",                    # strip all metadata
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", str(crf),
        "-g", str(gop),
        "-x264-params", "no-scenecut=1:qcomp=0.70",
        "-c:a", "aac",
        "-b:a", "128k",
        output_path
    ]

    return cmd, pitch_preserved
