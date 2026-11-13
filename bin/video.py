#!/usr/bin/env python3
"""Video schneiden, beschriften und ausspielen — ohne Premiere.

Drei Aufgaben, drei Befehle:

    python3 bin/video.py schnitt  roh.mov --ziel Reel.mp4
        Farbe nach PRESET, HDR nach SDR, Sprechpausen raus,
        0,25-Sekunden-Blenden an jedem Schnitt.

    python3 bin/video.py text     film.mp4 karten.json --ziel Fertig.mp4
        Schrift im Look von Soulful Radiance einbrennen.
        karten.json: [{"von": 0.2, "bis": 3.0, "text": "Zeile"}]

    python3 bin/video.py untertitel film.mp4 --sprache de --ziel Fertig.mp4
        Lokal transkribieren und als Schrift einbrennen.

Alles rechnet lokal. Keine Cloud, kein Abo.
"""
import argparse, json, os, re, subprocess, sys, tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import render

FF = render.FF
WURZEL = os.path.dirname(HIER)
FONTS = f"{WURZEL}/fonts"
WHISPER = os.environ.get("WHISPER_DIR", os.path.expanduser("~/.local/whisper.cpp"))

# Schriftbild aus LOOK.md, Hoehen wie in den Reels
GROESSE, RAND, GRUNDLINIE = 64, 80, 1260


def lauf(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(" ".join(cmd[:5]) + "\n" + r.stderr[-1800:])
    return r


def masse(quelle):
    r = subprocess.run([FF, "-hide_banner", "-i", quelle], capture_output=True, text=True)
    m = re.search(r", (\d{2,5})x(\d{2,5})", r.stderr)
    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    dreh = "rotation of -90" in r.stderr or "rotation of 90" in r.stderr
    b, h = (int(m.group(1)), int(m.group(2))) if m else (1080, 1920)
    if dreh: b, h = h, b
    laenge = int(d.group(1))*3600 + int(d.group(2))*60 + float(d.group(3)) if d else 0.0
    return b, h, laenge


# ------------------------------------------------------------ Pausen

def pausen_finden(quelle, schwelle=-30, mindest=0.18, rand=0.08, kuerzeste=0.35):
    """Sprechpausen suchen und die Stellen zurueckgeben, die bleiben.

    Werte aus PRESET.md: -30 dB ab 0,18 Sekunden. `rand` laesst vorne und
    hinten etwas Luft, damit keine Wortanfaenge abgeschnitten werden.
    """
    r = subprocess.run([FF, "-hide_banner", "-nostats", "-i", quelle,
                        "-af", f"silencedetect=noise={schwelle}dB:d={mindest}",
                        "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    enden  = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    _, _, L = masse(quelle)

    stillen = list(zip(starts, enden + ([L] if len(enden) < len(starts) else [])))
    behalten, zeiger = [], 0.0
    for a, b in stillen:
        a, b = a + rand, b - rand
        if a > zeiger:
            behalten.append([zeiger, a])
        zeiger = max(zeiger, b)
    if zeiger < L:
        behalten.append([zeiger, L])
    return [s for s in behalten if s[1] - s[0] >= kuerzeste]


# ------------------------------------------------------------ Schrift

def band_bauen(pfad, breite, hoehe, spitze=0.68):
    """Weicher dunkler Verlauf hinter der Schrift. Kein Kasten, keine Kante."""
    from PIL import Image
    oben  = int(hoehe * 0.505)
    voll1 = int(hoehe * 0.578)
    voll2 = int(hoehe * 0.693)
    unten = int(hoehe * 0.781)
    bild = Image.new("RGBA", (breite, hoehe), (0x0F, 0x0D, 0x0C, 0))
    px = bild.load()
    for y in range(hoehe):
        if y <= oben or y >= unten:   a = 0.0
        elif y < voll1:  a = ((y - oben) / (voll1 - oben)) ** 1.5 * spitze
        elif y <= voll2: a = spitze
        else:            a = ((unten - y) / (unten - voll2)) ** 1.5 * spitze
        v = int(round(a * 255))
        if v:
            for x in range(breite):
                px[x, y] = (0x0F, 0x0D, 0x0C, v)
    bild.save(pfad)
    return pfad


FAMILIE = "SR Sans"
SCHNITTE = {
    # ASS-Schnitt        Datei                        Stil           Gewicht
    "regular":     ("DMSans-Regular.ttf",      "Regular",     400),
    "bold":        ("DMSans-Black.ttf",        "Bold",        900),
    "italic":      ("DMSans-RegularItalic.ttf", "Italic",      400),
    "bolditalic":  ("DMSans-BlackItalic.ttf",  "Bold Italic", 900),
}


def schriftsatz(ordner):
    """Vier DM-Sans-Dateien zu einer Familie machen.

    Alle sieben Dateien heissen intern `DM Sans 9pt` und melden sich als
    Regular. libass kann daraus kein Fett und kein Kursiv ableiten. Also
    benennen wir Kopien um: ein Familienname, vier saubere Schnitte.
    """
    from fontTools.ttLib import TTFont
    os.makedirs(ordner, exist_ok=True)
    for schnitt, (datei, stil, gewicht) in SCHNITTE.items():
        f = TTFont(f"{FONTS}/{datei}")
        fett = "Bold" in stil
        kursiv = "Italic" in stil
        voll = f"{FAMILIE} {stil}"
        for eintrag in f["name"].names:
            if eintrag.nameID in (1, 16): eintrag.string = FAMILIE.encode("utf-16-be")
            elif eintrag.nameID in (2, 17): eintrag.string = stil.encode("utf-16-be")
            elif eintrag.nameID == 4: eintrag.string = voll.encode("utf-16-be")
            elif eintrag.nameID == 6:
                eintrag.string = voll.replace(" ", "").encode("utf-16-be")
        f["OS/2"].usWeightClass = gewicht
        wahl = f["OS/2"].fsSelection & ~0b1100001
        wahl |= (0b100000 if fett else 0) | (0b1 if kursiv else 0)
        if not fett and not kursiv: wahl |= 0b1000000   # REGULAR
        f["OS/2"].fsSelection = wahl
        f["head"].macStyle = (1 if fett else 0) | (2 if kursiv else 0)
        f.save(f"{ordner}/{schnitt}.ttf")
    return ordner


def auszeichnen(text):
    """*kursiv*, **fett**, ***beides*** in ASS-Marken uebersetzen."""
    import re as _re
    def tausch(m):
        sterne, wort = len(m.group(1)), m.group(2)
        auf = {1: "{\\i1}", 2: "{\\b1}", 3: "{\\b1\\i1}"}[sterne]
        zu  = {1: "{\\i0}", 2: "{\\b0}", 3: "{\\b0\\i0}"}[sterne]
        return auf + wort + zu
    return _re.sub(r"(\*{1,3})(.+?)\1", tausch, text)


def _blank(text):
    """Marken entfernen, um die reine Breite zu messen."""
    import re as _re
    return _re.sub(r"\*{1,3}", "", text)


def _breite(text, groesse, datei=f"{FONTS}/DMSans-Black.ttf"):
    from fontTools.ttLib import TTFont
    if not hasattr(_breite, "_f") or _breite._p != datei:
        _breite._f, _breite._p = TTFont(datei), datei
    f = _breite._f
    hm, cm, upm = f["hmtx"], f.getBestCmap(), f["head"].unitsPerEm
    return sum(hm[cm[ord(c)]][0] for c in text if ord(c) in cm) / upm * groesse


def _setzen(text, platz, groesse):
    """In hoechstens zwei Zeilen brechen, notfalls kleiner.

    Gemessen wird ohne die Sternchen, gesetzt wird mit.
    """
    for g in (groesse, groesse - 4, groesse - 8, groesse - 12):
        zeilen, zeile = [], ""
        for wort in text.split():
            probe = (zeile + " " + wort).strip()
            if zeile and _breite(_blank(probe), g) > platz:
                zeilen.append(zeile); zeile = wort
            else:
                zeile = probe
        if zeile: zeilen.append(zeile)
        if len(zeilen) <= 2:
            return zeilen, g
    return zeilen, g


def ass_bauen(karten, pfad, breite, hoehe, links=False):
    """Aus Zeiten und Text eine Untertiteldatei im Look bauen."""
    g = max(28, int(GROESSE * hoehe / 1920))
    rand = max(24, int(RAND * breite / 1080))
    unterkante = int(hoehe - GRUNDLINIE * hoehe / 1920)
    fett = 0
    if links:
        # Wie ihre MOFU-Reels: fett, groesser, links, auf Brusthoehe
        g = int(88 * hoehe / 1920); rand = int(100 * breite / 1080)
        unterkante = int(hoehe - 1130 * hoehe / 1920); fett = -1
    platz = breite - 2 * rand
    kopf = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {breite}
PlayResY: {hoehe}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: SR,{FAMILIE},{g},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,{fett},0,0,0,100,100,0,0,1,0,0,{1 if links else 2},{rand},{rand},{unterkante},1

[Events]
Format: Layer, Start, End, Style, MarginL, MarginR, MarginV, Effect, Text
"""
    def tc(x):
        x = max(0.0, x)
        return "%d:%02d:%05.2f" % (int(x//3600), int(x % 3600//60), x % 60)
    zeilen = []
    for k in karten:
        text = (k.get("text") or "").strip()
        if not text:
            continue
        # Zeichen entschaerfen, die ASS selbst benutzt. Muss vor dem
        # Umbruch passieren, damit unsere eigenen Marken heil bleiben.
        text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
        z, gg = _setzen(text, platz, g)
        # Erst zusammenfuegen, dann auszeichnen — sonst zerreisst ein
        # Zeilenumbruch ein Sternchenpaar.
        roh = auszeichnen("\\N".join(z))
        if gg != g:
            roh = "{\\fs%d}" % gg + roh
        zeilen.append(f"Dialogue: 0,{tc(k['von'])},{tc(k['bis'])},SR,,,,,{roh}")
    open(pfad, "w", encoding="utf-8").write(kopf + "\n".join(zeilen) + "\n")
    return pfad


def schrift_einbrennen(quelle, karten, ziel, crf=20, band=True, links=False):
    """Schrift ueber ein fertiges Video legen.

    `band` legt den weichen Verlauf darunter. Fuer Reels bleibt er aus —
    so sehen ihre Story-Reels aus: nur die weisse Schrift, sonst nichts.
    Auf sehr hellem Hintergrund kann die Schrift ohne Band untergehen.
    """
    b, h, _ = masse(quelle)
    with tempfile.TemporaryDirectory() as tmp:
        schrift = schriftsatz(f"{tmp}/schrift")
        ass = ass_bauen(karten, f"{tmp}/unter.ass", b, h, links=links)
        gemeinsam = ["-map", "[v]", "-map", "0:a?", "-c:v", "libx264",
                     "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", ziel]
        if band:
            bild = band_bauen(f"{tmp}/band.png", b, h)
            lauf([FF, "-hide_banner", "-loglevel", "error", "-stats", "-y",
                  "-i", quelle, "-i", bild, "-filter_complex",
                  f"[0:v]format=rgba[v0];[v0][1:v]overlay=0:0,format=yuv420p,"
                  f"subtitles=filename='{ass}':fontsdir='{schrift}'[v]"] + gemeinsam)
        else:
            lauf([FF, "-hide_banner", "-loglevel", "error", "-stats", "-y",
                  "-i", quelle, "-filter_complex",
                  f"[0:v]subtitles=filename='{ass}':fontsdir='{schrift}'[v]"] + gemeinsam)
    return ziel


# ------------------------------------------------------------ Transkript

def transkribieren(quelle, sprache="de", tmp=None, ml=46):
    """Lokal mit whisper.cpp. -mc 0 ist Pflicht, sonst dreht es bei langem
    Ton in Wiederholungsschleifen. VAD setzt die Zeiten auf echte Sprache."""
    tmp = tmp or tempfile.mkdtemp()
    wav = f"{tmp}/ton.wav"
    lauf([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", quelle,
          "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav])
    lauf([f"{WHISPER}/build/bin/whisper-cli",
          "-m", f"{WHISPER}/models/ggml-large-v3-turbo.bin", "-f", wav,
          "-l", sprache, "-t", "8", "-mc", "0", "-sns",
          "--vad", "--vad-model", f"{WHISPER}/models/ggml-silero-v5.1.2.bin",
          "--vad-min-silence-duration-ms", "300", "--vad-speech-pad-ms", "150",
          "-ml", str(ml), "-sow", "--output-srt", "--output-file", f"{tmp}/t"])
    karten = []
    for block in open(f"{tmp}/t.srt", encoding="utf-8").read().strip().split("\n\n"):
        z = block.strip().split("\n")
        if len(z) < 3:
            continue
        m = re.match(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)", z[1])
        if not m:
            continue
        v = [int(x) for x in m.groups()]
        karten.append({"von": v[0]*3600 + v[1]*60 + v[2] + v[3]/1000,
                       "bis": v[4]*3600 + v[5]*60 + v[6] + v[7]/1000,
                       "text": " ".join(z[2:]).strip()})
    return karten


# ------------------------------------------------------------ Befehle

def befehl_schnitt(a):
    segmente = pausen_finden(a.quelle, schwelle=a.schwelle, mindest=a.mindest)
    _, _, L = masse(a.quelle)
    behalten = sum(b - s for s, b in segmente)
    print(f"1 · {len(segmente)} Stellen bleiben, {behalten/60:.1f} von {L/60:.1f} Minuten")
    with tempfile.TemporaryDirectory() as tmp:
        teile = render.segmente_schneiden(a.quelle, segmente, tmp, breite=a.breite)
        print(f"2 · {len(teile)-1} Blenden à {render.BLENDE} s")
        render.blenden(teile, a.ziel)
    print(a.ziel)


def befehl_text(a):
    karten = json.load(open(a.karten))
    schrift_einbrennen(a.quelle, karten, a.ziel, band=not a.ohne_band)
    print(a.ziel)


def woerter_gruppieren(karten, n=3, zeichen=18):
    """Einzelwoerter zu kurzen Einblendungen wie in ihren MOFU-Reels:
    ein bis drei Woerter, nie ueber `zeichen` Zeichen, Satzende bricht."""
    raus, akt = [], None
    for k in karten:
        w = k["text"].strip()
        if not w:
            continue
        if akt and (len(akt["w"]) >= n or len(" ".join(akt["w"] + [w])) > zeichen
                    or akt["w"][-1][-1:] in ".?!,"):
            raus.append({"von": akt["von"], "bis": akt["bis"], "text": " ".join(akt["w"])}); akt = None
        if akt is None:
            akt = {"von": k["von"], "bis": k["bis"], "w": [w]}
        else:
            akt["w"].append(w); akt["bis"] = k["bis"]
    if akt:
        raus.append({"von": akt["von"], "bis": akt["bis"], "text": " ".join(akt["w"])})
    for a, b in zip(raus, raus[1:]):
        a["bis"] = max(a["bis"], min(b["von"], a["bis"] + 0.4))
    return raus


def befehl_untertitel(a):
    with tempfile.TemporaryDirectory() as tmp:
        print("1 · lokal transkribieren")
        if a.woerter:
            karten = woerter_gruppieren(transkribieren(a.quelle, a.sprache, tmp, ml=1), n=a.woerter)
        else:
            karten = transkribieren(a.quelle, a.sprache, tmp)
        print(f"2 · {len(karten)} Einblendungen einbrennen")
        if a.nur_text:
            json.dump(karten, open(a.nur_text, "w"), ensure_ascii=False, indent=1)
            print(a.nur_text); return
        schrift_einbrennen(a.quelle, karten, a.ziel, band=not a.ohne_band and not a.woerter, links=bool(a.woerter))
    print(a.ziel)


def main():
    p = argparse.ArgumentParser(description="Video schneiden ohne Premiere")
    u = p.add_subparsers(dest="befehl", required=True)

    s = u.add_parser("schnitt", help="Farbe, Pausen raus, weiche Blenden")
    s.add_argument("quelle"); s.add_argument("--ziel", required=True)
    s.add_argument("--breite", type=int, default=1080)
    s.add_argument("--schwelle", type=float, default=-30)
    s.add_argument("--mindest", type=float, default=0.18)
    s.set_defaults(f=befehl_schnitt)

    t = u.add_parser("text", help="Schrift im Look einbrennen")
    t.add_argument("quelle"); t.add_argument("karten")
    t.add_argument("--ziel", required=True)
    t.add_argument("--ohne-band", dest="ohne_band", action="store_true",
                   help="kein Verlauf hinter der Schrift, wie in den Reels")
    t.set_defaults(f=befehl_text)

    v = u.add_parser("untertitel", help="lokal transkribieren und einbrennen")
    v.add_argument("quelle"); v.add_argument("--ziel")
    v.add_argument("--sprache", default="de")
    v.add_argument("--nur-text", dest="nur_text",
                   help="nur die Textdatei schreiben, nichts rendern")
    v.add_argument("--ohne-band", dest="ohne_band", action="store_true",
                   help="kein Verlauf hinter der Schrift, wie in den Reels")
    v.add_argument("--woerter", type=int, default=0,
                   help="Stil der MOFU-Reels: 1 bis N Woerter, links, ohne Band (3 empfohlen)")
    v.set_defaults(f=befehl_untertitel)

    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
