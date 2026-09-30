import os
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
HERO_DIR = BASE_DIR / "static" / "videos" / "hero"
HERO_DIR.mkdir(parents=True, exist_ok=True)

SHOWCASES = [
    {
        "day": 0,
        "name": "hero_day_0_ankaport.mp4",
        "src": BASE_DIR / "static/projeler/ANKAPORT - SARAY/TANITIM - ANKAPORT SARAY.mp4",
        "start": "00:00:04",
        "duration": "16"
    },
    {
        "day": 1,
        "name": "hero_day_1_spoint.mp4",
        "src": BASE_DIR / "static/projeler/S POINT - VIP SARAY/TANITIM - S POINT.mp4",
        "start": "00:00:05",
        "duration": "16"
    },
    {
        "day": 2,
        "name": "hero_day_2_narcin.mp4",
        "folder_kw": "RONYA",
        "file_kw": "SUNUM",
        "start": "00:00:08",
        "duration": "16"
    },
    {
        "day": 3,
        "name": "hero_day_3_grande.mp4",
        "src": BASE_DIR / "static/projeler/GRANDE YAŞAMKENT/TANITIM - GRANDE YAŞAMKENT.mp4",
        "start": "00:00:03",
        "duration": "16"
    },
    {
        "day": 4,
        "name": "hero_day_4_gokdemir.mp4",
        "src": BASE_DIR / "static/projeler/GÖKDEMİR İMZA/TANITIM - GÖKDEMİR İMZA.mp4",
        "start": "00:00:05",
        "duration": "16"
    },
    {
        "day": 5,
        "name": "hero_day_5_evart.mp4",
        "src": BASE_DIR / "static/projeler/EVART YALIKAVAK/TANITIM - EVART YALIKAVAK.mp4",
        "start": "00:00:05",
        "duration": "16"
    },
    {
        "day": 6,
        "name": "hero_day_6_idea.mp4",
        "src": BASE_DIR / "static/projeler/IDEA - START BRAVO/TANITIM - IDEA - START BRAVO.mp4",
        "start": "00:00:05",
        "duration": "16"
    }
]

def generate_all():
    print(f"[*] Processing 7 daily hero web loops into {HERO_DIR}...")
    for item in SHOWCASES:
        out_path = HERO_DIR / item["name"]
        src_path = item.get("src")
        if not src_path or not src_path.exists():
            if item.get("folder_kw"):
                f_kw = item["folder_kw"].lower()
                for d in (BASE_DIR / "static/projeler").iterdir():
                    if d.is_dir() and f_kw in d.name.lower():
                        for f in d.glob("*.mp4"):
                            if item.get("file_kw") and item["file_kw"].lower() in f.name.lower():
                                src_path = f
                                break
                            elif not item.get("file_kw"):
                                src_path = f
                                break
                        if src_path:
                            break
        if not src_path or not src_path.exists():
            print(f"[!] Source missing for Day {item['day']}")
            continue

        vf_scale = "scale=-2:720" if item.get("day") == 3 else "scale=1280:-2"
        cmd = [
            "ffmpeg", "-y",
            "-ss", item["start"],
            "-i", str(src_path),
            "-t", item["duration"],
            "-c:v", "libx264",
            "-crf", "26",
            "-preset", "faster",
            "-pix_fmt", "yuv420p",
            "-vf", vf_scale,
            "-c:a", "aac",
            "-b:a", "64k",
            "-ac", "2",
            "-movflags", "+faststart",
            str(out_path)
        ]
        print(f"[*] Encoding Day {item['day']}: {item['name']}...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0:
            sz_mb = out_path.stat().st_size / (1024 * 1024)
            print(f"[+] Day {item['day']} SUCCESS: {item['name']} ({sz_mb:.2f} MB)")
        else:
            print(f"[-] Day {item['day']} FAILED. Stderr: {res.stderr.decode('utf-8', errors='ignore')[-300:]}")

if __name__ == "__main__":
    generate_all()
