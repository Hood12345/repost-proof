# utils/ffmpeg_mods.py
import random
import subprocess


# ─────────────────────────────────────────────────────────────────── helpers
def has_rubberband() -> bool:
    """Return True if FFmpeg was built with the rubberband filter (pitch-preserve)."""
    try:
        out = subprocess.check_output(["ffmpeg", "-filters"], stderr=subprocess.DEVNULL)
        return b"rubberband" in out
    except Exception:
        return False


# ─────────────────────────────────────────────────────────── main builder
def build_ffmpeg_command(input_path: str, output_path: str):
    """
    Build an FFmpeg command that adds subtle, randomized variations
    (spatial, temporal, colour, audio) to escape perceptual hashes
    while retaining human-visible quality.

    Returns (cmd_list, pitch_preserved_bool)
    """

    # ── encode-level randomness ────────────────────────────────────────────
    crf = random.choice([22, 23, 24])
    gop = random.choice([24, 48, 72])

    # ── video filters (all tiny, but hash-breaking) ────────────────────────
    zoom = round(random.uniform(1.015, 1.035), 3)           # 1–3 % zoom-crop
    frame_shift = random.randint(-3, 3)                     # ±3-frame shift
    noise_strength = random.randint(2, 4)                   # low-gain noise

    sat = round(random.uniform(0.995, 1.01), 3)             # ≤1 % jitter
    bri = round(random.uniform(0.995, 1.01), 3)
    con = round(random.uniform(1.00, 1.02), 3)

    crop_pad = (
        "crop=iw-2:ih-2,"
        "pad=iw+2:ih+2:1:1,"
        "drawbox=x=10:y=10:w=5:h=5:color=white@0.001:t=fill"
    )

    vf_parts = [
        f"scale=iw*{zoom}:ih*{zoom},crop=iw/{zoom}:ih/{zoom}",
        f"setpts=PTS+{frame_shift}/TB" if frame_shift else "",
        crop_pad,
        f"noise=alls={noise_strength}:allf=t+u",
        f"eq=brightness={bri}:contrast={con}:saturation={sat}",
        "unsharp=5:5:0.8:5:5:0.0",   # mild sharpen
        "deband",                    # smooth banding
        "format=yuv420p"             # normalise colour planes
    ]
    vfilter = ",".join([p for p in vf_parts if p])

    # ── audio filters (random tempo; preserve pitch if possible) ───────────
    tempo = round(random.uniform(0.987, 1.013), 3)          # ±1.3 % tempo
    audio_filters = [f"atempo={tempo}",
                     "equalizer=f=200:t=q:w=1:g=1",
                     "dcshift=0.01:0"]

    if has_rubberband():
        audio_filters.insert(0, f"rubberband=tempo={tempo}")
        pitch_preserved = True
    else:
        audio_filters.insert(1, f"asetrate=44100/{tempo},aresample=44100")
        pitch_preserved = False

    afilter = ",".join(audio_filters)

    # ── final ffmpeg command list ──────────────────────────────────────────
    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-i", input_path,
        "-vf", vfilter,
        "-af", afilter,
        "-map_metadata", "-1",                       # strip metadata
        "-c:v", "libx264", "-preset", "veryfast",
        "-crf", str(crf), "-g", str(gop),
        "-x264-params", "no-scenecut=1:qcomp=0.70",  # destroy watermark bits
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ]

    return cmd, pitch_preserved
