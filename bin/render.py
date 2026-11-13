#!/usr/bin/env python3
"""Schneidet und rendert ein Video komplett ohne Premiere.
Pausen raus · 0,25-s-Blenden · Farbe nach PRESET · HDR nach SDR."""
import json, os, subprocess, sys, time

FF = os.environ.get("FFMPEG") or (os.path.expanduser("~/.local/bin/ffmpeg") if os.path.exists(os.path.expanduser("~/.local/bin/ffmpeg")) else "ffmpeg")
GRADE = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "grade.json")))
BLENDE = 0.25

def lauf(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-1500:])
    return r

def ist_hdr(quelle):
    r = subprocess.run([FF, "-hide_banner", "-i", quelle], capture_output=True, text=True)
    return any(k in r.stderr for k in ("bt2020", "arib-std-b67", "smpte2084"))


def segmente_schneiden(quelle, segmente, arbeit, breite=1080):
    os.makedirs(arbeit, exist_ok=True)
    stufen = [f"scale={breite}:-2"]
    if ist_hdr(quelle):
        stufen.append(GRADE["tonemap"])
        print("   HDR erkannt → Umsetzung nach SDR")
    else:
        print("   Quelle ist bereits SDR → keine Umsetzung")
    stufen.append(GRADE["ffmpeg"])
    kette = ",".join(stufen)
    teile = []
    for i, (a, b) in enumerate(segmente):
        aus = f"{arbeit}/s{i:03d}.mp4"
        lauf([FF, "-hide_banner", "-loglevel", "error", "-y",
              "-ss", f"{a:.3f}", "-i", quelle, "-t", f"{b-a:.3f}",
              "-vf", kette, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
              "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", aus])
        teile.append((aus, b - a))
        print(f"   {i+1}/{len(segmente)}  {b-a:5.2f} s", flush=True)
    return teile

def blenden(teile, ziel, blende=BLENDE):
    ein, fc, v, a = [], [], "[0:v]", "[0:a]"
    for p, _ in teile:
        ein += ["-i", p]
    laufzeit = teile[0][1]
    for i in range(1, len(teile)):
        off = laufzeit - blende
        fc.append(f"{v}[{i}:v]xfade=transition=fade:duration={blende}:offset={off:.3f}[v{i}]")
        fc.append(f"{a}[{i}:a]acrossfade=d={blende}:c1=tri:c2=tri[a{i}]")
        v, a = f"[v{i}]", f"[a{i}]"
        laufzeit = laufzeit + teile[i][1] - blende
    cmd = [FF, "-hide_banner", "-loglevel", "error", "-y"] + ein
    if fc:
        cmd += ["-filter_complex", ";".join(fc), "-map", v, "-map", a]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "19",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", ziel]
    lauf(cmd)
    return laufzeit

if __name__ == "__main__":
    quelle, segdatei, ziel, arbeit = sys.argv[1:5]
    segmente = json.load(open(segdatei))
    t0 = time.time()
    print(f"1 · {len(segmente)} Segmente schneiden, Farbe und HDR-Umsetzung")
    teile = segmente_schneiden(quelle, segmente, arbeit)
    print(f"2 · {len(teile)-1} Blenden à {BLENDE} s")
    L = blenden(teile, ziel)
    print(f"fertig: {ziel}  ·  {L:.1f} s  ·  {time.time()-t0:.0f} s Rechenzeit")
