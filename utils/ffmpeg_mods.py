import random, subprocess, uuid, os

# ───────────────────────────────────────────────────────── helpers
def has_rubberband() -> bool:
    try:
        out = subprocess.check_output(["ffmpeg", "-filters"], stderr=subprocess.DEVNULL)
        return b"rubberband" in out
    except Exception:
        return False

def generate_valid_lut3d_file() -> str:
    lut_path = f"/tmp/lut_{uuid.uuid4().hex}.cube"
    with open(lut_path, "w") as f:
        f.write("TITLE \"Safe Random 2x2x2 LUT\"\n")
        f.write("LUT_3D_SIZE 2\n")
        f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write("DOMAIN_MAX 1.0 1.0 1.0\n")
        for r in [0.0, 1.0]:
            for g in [0.0, 1.0]:
                for b in [0.0, 1.0]:
                    # Tiny color variation within safe range
                    dr = max(0.0, min(1.0, r + random.uniform(-0.005, 0.005)))
                    dg = max(0.0, min(1.0, g + random.uniform(-0.005, 0.005)))
                    db = max(0.0, min(1.0, b + random.uniform(-0.005, 0.005)))
                    f.write(f"{dr:.6f} {dg:.6f} {db:.6f}\n")
    return lut_path

# ───────────────────────────────────────────────────────── builder
def build_ffmpeg_command(input_path: str, output_path: str):
    crf = random.choice([22, 23, 24])
    gop = random.choice([24, 48, 72])

    zoom        = round(random.uniform(1.015, 1.025), 3)
    frame_shift = random.randint(-2, 2)
    noise_s     = random.randint(1, 2)
    sat = round(random.uniform(0.995, 1.01), 3)
    bri = round(random.uniform(0.997, 1.01), 3)
    con = round(random.uniform(1.00,  1.015), 3)
    flip_intvl  = random.randint(90, 120)

    lut_path = generate_valid_lut3d_file()

    crop_pad_draw = (
        "crop=iw-2:ih-2,"
        "pad=iw+2:ih+2:1:1,"
        "drawbox=x=10:y=10:w=5:h=5:color=white:t=fill"
    )

    # ─────────────────────────────────────── video filter chain
    vf_filters = [
        f"scale=iw*{zoom}:ih*{zoom},crop=iw/{zoom}:ih/{zoom}",
        f"setpts=PTS+{frame_shift}/TB" if frame_shift else "",
        f"tblend=all_mode=average,select=not(mod(n\\,{flip_intvl})),hflip,tblend=all_mode=average" if flip_intvl else "",
        f"lut3d={lut_path}",
        crop_pad_draw,
        f"noise=alls={noise_s}:allf=t+u",
        f"eq=brightness={bri}:contrast={con}:saturation={sat}",
        "unsharp=5:5:0.8:5:5:0.0",
        "deband",
        "format=yuv420p"
    ]

    vf = ",".join(filter(None, vf_filters))

    # ─────────────────────────────────────── audio filters
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
    pitch_preserved = False

    # ─────────────────────────────────────── full command
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
