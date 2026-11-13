# Reels-Schnitt

Nur die Schnitt-Werkzeuge von Soulful Radiance. Keine Kundendaten, keine Abschriften, keine Gespräche.

- `bin/video.py schnitt roh.mov --ziel Reel.mp4` · Farbe nach PRESET.md, Sprechpausen raus
- `bin/video.py text film.mp4 karten.json --ziel Fertig.mp4` · Schrift einbrennen
- `bin/video.py untertitel film.mp4 --sprache de --ziel Fertig.mp4` · Untertitel über whisper.cpp

Umgebung: `FFMPEG` (sonst ffmpeg aus dem PATH), `WHISPER_DIR` (whisper.cpp mit Modell).
