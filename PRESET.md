# Standard-Ablauf · gilt für jedes Video

Von Empress festgelegt am 4. September 2026. Wird bei jedem Auftrag angewandt,
ohne dass sie es wiederholen muss.

## 1. Farbe zuerst

**Nicht mehr abdunkeln.** Am 20. Oktober 2026 geändert — das Abdunkeln machte das Bild flau statt wärmer. Nur noch ein Hauch Kontrast und Sättigung. Grundwerte aus LOOK.md Punkt 4:

| | |
|---|---|
| Belichtung | 0 (war −0,3, am 20.10.2026 geändert) |
| Kontrast | −8 |
| Lichter | −15 |
| Tiefen | +25 |
| Weiß | +10 |
| Schwarz | +12 |
| Sättigung | 92 |

Bei HDR-Material zusätzlich die Umsetzung nach SDR, sonst wirkt das Bild flau.
Werte liegen in `jobs/grade.json`, die Renderstrecke liest sie von dort.

## 2. Schnitt

- Alle Sprechpausen raus. Schwelle −30 dB ab 0,18 Sekunden.
- Keine doppelten Sätze. Wenn derselbe Gedanke zweimal kommt, bleibt die bessere Fassung.
- Keine Versprecher, keine abgebrochenen Wörter.
- Es muss zusammenhängend bleiben. Lieber eine Pause stehen lassen als einen Satz zerreißen.

## 3. Übergänge weich

Keine harten Schnitte zwischen Talking-Head-Einstellungen mehr. Cross Dissolve,
0,25 Sekunden, an jedem Schnittpunkt. Ton blendet mit.

Das ersetzt die frühere Regel aus LOOK.md Punkt 6 und 8, die harte Schnitte verlangte.

## 4. Special Effects — immer vorher fragen

Bevor ich irgendeinen Effekt einbaue — Wackler, Zoom, Blitz, Geschwindigkeit,
Übergangsspielereien — frage ich Empress vorher. Auch wenn sie „mach alles selbst"
gesagt hat. Effekte sind Geschmack, nicht Handwerk.

Gilt nicht für den Standardablauf: Farbe, Pausenschnitt und die 0,25-Sekunden-Blende
laufen ohne Rückfrage.

## 5. Ablageort

Alles Fertige kommt **direkt nach `~/Downloads`** — keine Unterordner, nichts im
Projektordner. Am 21. Oktober 2026 geschärft: Empress schaut in keinen anderen
Ordner. Gilt für Videos, Untertitel, Bilder und Vergleiche gleichermaßen.

## 6. Untertitel

Macht Empress selbst. Ich setze keine.

---

## Was wo läuft

Seit 3. November 2026 nichts mehr in Premiere. Farbe, Pausenschnitt, Blenden,
Schrift und Export rechnet die lokale Strecke:

- `python3 bin/video.py schnitt` — Farbe, HDR nach SDR, Pausen raus, 0,25-s-Blenden
- `python3 bin/video.py text` — Schrift im Look einbrennen
- `python3 bin/video.py untertitel` — lokal transkribieren und einbrennen
- `python3 bin/ton.py` — Stimme putzen, Pegel setzen, Musikbett legen (statt Audition)

Vollständig beschrieben in `WERKZEUG.md`.
