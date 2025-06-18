# utils/ffmpeg_mods.py
import random
import subprocess
import uuid


# ───────────────────────────────────────────────────────── helpers
def has_rubberband() -> bool:
    """Return True if FFmpeg was built with the rubberband filter."""
    try:
        out = subprocess.check_output(["ffmpeg", "-filters"], stderr=subprocess.DEVNULL)
        return b"rubberband" in out
    except Exception:
        return False


# ───────────────────────────────────────────────────────── builder
def build_ffmpeg_command(input_path: str, output_path: str):
    """
    Build an FFmpeg command that keeps the original look,
    but adds subtle randomness so Instagram’s hash cannot match.
    Returns (cmd_list, pitch_preserved_bool)
    """

    # ── encode randomness (quality still high) ────────────────────────────
    crf = random.choice([22, 23, 24])
    gop = random.choice([24, 48, 72])

    # ── video randomness (all imperceptible) ──────────────────────────────
    zoom        = round(random.uniform(1.015, 1.028), 3)   # 1.5–2.8 % zoom-crop
    frame_shift = random.randint(-2, 2)                    # ±2-frame offset
    noise_s     = random.randint(2, 3)                     # very light noise

    sat = round(random.uniform(0.995, 1.01), 3)            # ≤1 % jitter
    bri = round(random.uniform(0.995, 1.01), 3)
    con = round(random.uniform(1.00,  1.02), 3)

    # Optional 1-frame flip blend (invisible, skip 20 % of jobs)
    flip_part = ""
    if random.random() < 0.8:  # 80 % chance to include
        flip_intvl = random.randint(90, 120)
        flip_part = (f"tblend=all_mode=average,"
                     f"select='not(mod(n\\,{flip_intvl}))',hflip,"
                     f"tblend=all_mode=average")

    # Keep your original crop-pad-drawbox trick
    crop_pad_draw = (
        "crop=iw-2:ih-2,"
        "pad=iw+2:ih+2:1:1,"
        "drawbox=x=10:y=10:w=5:h=5:color=white@0.001:t=fill"
    )

    # Assemble video filters
    vf_parts = [
        f"scale=iw*{zoom}:ih*{zoom},crop=iw/{zoom}:ih/{zoom}",
        f"setpts=PTS+{frame_shift}/TB" if frame_shift else "",
        crop_pad_draw,
        flip_part,
        f"noise=alls={noise_s}:allf=t+u",
        f"eq=brightness={bri}:contrast={con}:saturation={sat}",
        "unsharp=5:5:0.8:5:5:0.0",
        "deband",
        "format=yuv420p"   # ensure valid colour planes
    ]
    vfilter = ",".join([p for p in vf_parts if p])

    # ── audio randomness (inaudible) ───────────────────────────────────────
    tempo = round(random.uniform(0.987, 1.013), 3)        # ±1.3 % tempo
    micro = round(random.uniform(0.9993, 1.0007), 6)      # ±30 Hz pitch

    audio_filters = [
        f"atempo={tempo}",
        f"asetrate=44100*{micro},aresample=44100",
        "equalizer=f=200:t=q:w=1:g=1",
        "dcshift=0.01:0"
    ]

    if has_rubberband():
        audio_filters.insert(0, f"rubberband=tempo={tempo}")

    afilter = ",".join(audio_filters)
    pitch_preserved = False  # micro shift technically alters pitch < 0.1 %

    # ── final command list ────────────────────────────────────────────────
    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-i", input_path,
        "-vf", vfilter,
        "-af", afilter,
        "-map_metadata", "-1",                     # strip metadata
        "-c:v", "libx264", "-preset", "veryfast",
        "-crf", str(crf), "-g", str(gop),
        "-x264-params", "no-scenecut=1:qcomp=0.70",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ]

    return cmd, pitch_preserved
