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
    # Random parameters
    crf = random.choice([22, 23, 24])
    gop = random.choice([24, 48, 72])

    audio_filters = [
        "atempo=1.01",
        "equalizer=f=200:t=q:w=1:g=1",
        "dcshift=0.01:0"
    ]

    if has_rubberband():
        audio_filters.insert(0, "rubberband=tempo=1.01")
        pitch_preserved = True
    else:
        audio_filters.insert(1, "asetrate=44100/1.01,aresample=44100")
        pitch_preserved = False

    afilter = ",".join(audio_filters)

    vfilter = ",".join([
        "crop=iw-2:ih-2",
        "pad=iw+2:ih+2:1:1",
        "drawbox=x=10:y=10:w=5:h=5:color=white@0.001:t=fill",  # ✅ FIXED here
        "noise=alls=10:allf=t+u",
        "eq=brightness=0.01:contrast=1.01",
        "hue=s=1.01"
    ])

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
