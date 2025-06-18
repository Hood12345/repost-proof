import random, subprocess, uuid, os

def has_rubberband():
    try:
        out = subprocess.check_output(["ffmpeg", "-filters"], stderr=subprocess.DEVNULL)
        return b"rubberband" in out
    except Exception:
        return False

def build_ffmpeg_command(input_path: str, output_path: str):
    crf = random.choice([22, 23, 24])
    gop = random.choice([24, 48, 72])

    # Conservative, but randomized filters
    zoom = round(random.uniform(1.005, 1.012), 3)
    noise = random.randint(1, 3)
    bri = round(random.uniform(0.995, 1.01), 3)
    con = round(random.uniform(1.0, 1.02), 3)
    sat = round(random.uniform(0.99, 1.02), 3)

    vf_filters = [
        f"scale=iw*{zoom}:ih*{zoom},crop=iw/{zoom}:ih/{zoom}",  # subtle zoom
        "crop=iw-2:ih-2",
        "pad=iw+2:ih+2:1:1",
        "drawbox=x=10:y=10:w=5:h=5:color=white@0.001:t=fill",  # hidden watermark
        f"noise=alls={noise}:allf=t+u",
        f"eq=brightness={bri}:contrast={con}:saturation={sat}",
        "unsharp=5:5:0.8:5:5:0.0",
        "deband",
        "format=yuv420p",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2"
    ]

    tempo = round(random.uniform(0.99, 1.011), 3)
    micro = round(random.uniform(0.9993, 1.0007), 6)

    afilters = [
        f"atempo={tempo}",
        f"asetrate=44100*{micro},aresample=44100",
        "equalizer=f=200:t=q:w=1:g=1",
        "dcshift=0.01:0"
    ]
    if has_rubberband():
        afilters.insert(0, f"rubberband=tempo={tempo}")

    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-i", input_path,
        "-vf", ",".join(vf_filters),
        "-af", ",".join(afilters),
        "-map_metadata", "-1",
        "-c:v", "libx264", "-preset", "veryfast",
        "-crf", str(crf), "-g", str(gop),
        "-x264-params", "no-scenecut=1:qcomp=0.70",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ]

    return cmd, False
