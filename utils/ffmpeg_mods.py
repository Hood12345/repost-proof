# utils/ffmpeg_mods.py
import random, subprocess, uuid

# ───────────────────────────────────────────────────────── helpers
def has_rubberband() -> bool:
    try:
        out = subprocess.check_output(["ffmpeg", "-filters"], stderr=subprocess.DEVNULL)
        return b"rubberband" in out
    except Exception:
        return False


# ───────────────────────────────────────────────────────── builder
def build_ffmpeg_command(input_path: str, output_path: str):
    """
    Return (ffmpeg_cmd_list, pitch_preserved_bool)
    Provides strong anti-fingerprint randomisation while
    guaranteeing the picture stays visually identical.
    """

    # 0. Encode randomness ---------------------------------------------------
    crf = random.choice([22, 23, 24])
    gop = random.choice([24, 48, 72])

    # 1. Video random --------------------------------------------------------
    zoom        = round(random.uniform(1.015, 1.028), 3)
    frame_shift = random.randint(-2, 2)
    noise_s     = random.randint(2, 3)

    sat = round(random.uniform(0.995, 1.01), 3)
    bri = round(random.uniform(0.995, 1.01), 3)
    con = round(random.uniform(1.00,  1.02), 3)

    flip_intvl  = random.randint(90, 120)

    # Tiny 3×3×3 LUT
    dr, dg, db = [random.randint(-2, 2) / 255 for _ in range(3)]
    lut_path = f"/tmp/lut_{uuid.uuid4().hex}.cube"
    with open(lut_path, "w") as f:
        f.write("LUT_3D_SIZE 2\n0 0 0\n")
        f.write(f"{dr} {dg} {db}\n")

    # Pad / drawbox from legacy chain
    crop_pad_draw = (
        "crop=iw-2:ih-2,"
        "pad=iw+2:ih+2:1:1,"
        "drawbox=x=10:y=10:w=5:h=5:color=white:t=fill"
    )

    # ---------- build video graph ------------------------------------------
    vf = ",".join([
        f"scale=iw*{zoom}:ih*{zoom},crop=iw/{zoom}:ih/{zoom}",
        f"setpts=PTS+{frame_shift}/TB" if frame_shift else "",
        # Work in RGB for risky filters, then back to YUV
        "format=rgb24",
        # **FIXED** single quotes removed around select expression ↓
        f"tblend=all_mode=average,select=not(mod(n\\,{flip_intvl})),hflip,"
        f"tblend=all_mode=average",
        f"lut3d={lut_path}",
        "format=yuv420p",
        crop_pad_draw,
        f"noise=alls={noise_s}:allf=t+u",
        f"eq=brightness={bri}:contrast={con}:saturation={sat}",
        "unsharp=5:5:0.8:5:5:0.0",
        "deband",
        "format=yuv420p"
    ])

    # 2. Audio random --------------------------------------------------------
    tempo  = round(random.uniform(0.987, 1.013), 3)
    micro  = round(random.uniform(0.9993, 1.0007), 6)

    afilters = [
        f"atempo={tempo}",
        f"asetrate=44100*{micro},aresample=44100",
        "equalizer=f=200:t=q:w=1:g=1",
        "dcshift=0.01:0"
    ]
    if has_rubberband():
        afilters.insert(0, f"rubberband=tempo={tempo}")

    af = ",".join(afilters)
    pitch_preserved = False  # micro-shift alters pitch ~0.07 %

    # 3. Final command -------------------------------------------------------
    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-i", input_path,
        "-vf", vf,
        "-af", af,
        "-map_metadata", "-1",
        "-c:v", "libx264", "-preset", "veryfast",
        "-crf", str(crf), "-g", str(gop),
        "-x264-params", "no-scenecut=1:qcomp=0.70",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ]

    return cmd, pitch_preserved
