import os
import random
import subprocess

def has_rubberband():
    try:
        output = subprocess.check_output(['ffmpeg', '-filters'], stderr=subprocess.DEVNULL)
        return b"rubberband" in output
    except:
        return False

def build_ffmpeg_command(input_path, output_path):
    # Randomized video encoding params
    crf = random.choice([22, 23, 24])
    gop = random.choice([24, 48, 72])

    # Randomized visual tweaks
    brightness = round(random.uniform(0.005, 0.015), 3)
    contrast   = round(random.uniform(1.005, 1.015), 3)
    saturation = round(random.uniform(1.005, 1.015), 3)
    hue_shift  = round(random.uniform(0.99, 1.01), 3)
    noise_lvl  = random.randint(6, 12)

    # Audio filter randomization
    tempo_variation = round(random.uniform(0.99, 1.01), 3)
    pitch_shift     = round(random.uniform(0.999, 1.001), 6)

    audio_filters = [
        f"atempo={tempo_variation}",
        "equalizer=f=200:t=q:w=1:g=1",
        "dcshift=0.01:0"
    ]

    if has_rubberband():
        audio_filters.insert(0, f"rubberband=tempo={tempo_variation}")
        pitch_preserved = True
    else:
        audio_filters.insert(1, f"asetrate=44100*{pitch_shift},aresample=44100")
        pitch_preserved = False

    afilter = ",".join(audio_filters)

    # Final video filter chain
    vfilter = ",".join([
        "crop=iw-2:ih-2",
        "pad=iw+2:ih+2:1:1",
        "drawbox=x=10:y=10:w=5:h=5:color=white@0.001:t=fill",
        f"noise=alls={noise_lvl}:allf=t+u",
        f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}",
        f"hue=s={hue_shift}"
    ])

    # Build full FFmpeg command
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", vfilter,
        "-af", afilter,
        "-map_metadata", "-1",
        "-c:v", "libx264",
        "-crf", str(crf),
        "-g", str(gop),
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "128k",
        output_path
    ]

    return cmd, pitch_preserved
