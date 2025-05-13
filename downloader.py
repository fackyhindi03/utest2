import os
import subprocess
import requests

def remux_hls(m3u8_url: str, referer: str, output_path: str):
    cmd = [
        "ffmpeg", "-y",
        "-headers", f"Referer: {referer}",
        "-i", m3u8_url,
        "-c", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True)
    return output_path

def download_subtitle(track: dict, out_dir: str, episode_id: str):
    url = track.get("file") or track.get("url")
    resp = requests.get(url)
    resp.raise_for_status()
    fname = os.path.basename(url)
    path = os.path.join(out_dir, fname)
    with open(path, "wb") as f:
        f.write(resp.content)
    return path
