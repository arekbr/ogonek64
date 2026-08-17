#!/usr/bin/env python3
"""ogonek64 — generator fontów TrueType z tekstowego źródła glifów.

Czyta src/glify-{baza,dodatki,pl}.txt i buduje rodziny:

  Ogonek 64 Mono   Regular / Bold   stała szerokość, do terminala i kodu
  Ogonek 64 Sans   Regular          szerokość liczona per litera
  Ogonek 64 CRT    Regular          linie wygaszenia + poświata kineskopu

── GEOMETRIA ────────────────────────────────────────────────────────────────
unitsPerEm 2048, 1 piksel = 256 jednostek, komórka 8 x 10 pikseli.
Linia bazowa leży pod wierszem 7 (spód wielkiej litery). Wiersz źródłowy `i`
zajmuje y od (7-i)*256 do (8-i)*256, więc:

  wiersz 0      2048 .. 1792   akcent nad wielką literą   -> ascender  2048
  wiersze 1..7  1792 ..    0   korpus                     -> capHeight 1792
  wiersz 8         0 ..  -256  descender (g j p q y)
  wiersz 9      -256 ..  -512  dolny wiersz ogonka        -> descender -512

Wysokość całkowita 2560 = 10 px = interlinia 1.25 em. To cena za nietknięte
kształty bazowe i akcenty o pełnej grubości 2 px.

Piksele NIE są zapisywane jako osobne prostokąty — najpierw scalam je w poziome
ciągi, potem w pionowe bloki, a na końcu `removeOverlaps` (skia-pathops) zlepia
je w jeden czysty kontur na glif. Bez tego font miałby setki stykających się
krawędzi, na których rasteryzery robią artefakty.
"""
import os, sys, re
from datetime import datetime, timezone

KAT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KAT, "lib"))
from zrob_glify import czytaj, SZER, WYS

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.removeOverlaps import removeOverlaps
from fontTools.agl import UV2AGL

PX        = 256                 # jednostek na piksel
UPM       = SZER * PX           # 2048
BASELINE  = 7                   # wiersz, pod którym leży linia bazowa

# Odstęp między akcentem a literą. Nad WIELKĄ literą w siatce 8x10 nie ma wolnego
# wiersza — akcent siedzi tuż nad korpusem i wizualnie się z nim zlewa (Ż wygląda
# jak Z z guzem). Ten parametr podnosi SAM wiersz akcentu o 1 px, rosnąc ascender
# do 9 px. 0 = ciasno, po retro; 256 = z odstępem, typograficznie poprawnie.
ODSTEP_AKCENTU = int(os.environ.get("OGONEK_ODSTEP", "256"))
ASCENDER  = 2048 + ODSTEP_AKCENTU
DESCENDER = -512
CAP       = 1792
XHEIGHT   = 1280
WERSJA    = "1.001"
ROK       = 2026

# ── geometria ────────────────────────────────────────────────────────────────
def _o(i):      return ODSTEP_AKCENTU if i == 0 else 0
def y_gora(i):  return (BASELINE + 1 - i) * PX + _o(i)
def y_dol(i):   return (BASELINE - i) * PX + _o(i)

def runy(wiersz):
    """poziome ciągi zapalonych pikseli: '.##..##.' -> [(1,3),(5,7)]"""
    out, start = [], None
    for j, c in enumerate(wiersz):
        if c == "#" and start is None:
            start = j
        elif c != "#" and start is not None:
            out.append((start, j)); start = None
    if start is not None:
        out.append((start, SZER))
    return out

def bloki(g):
    """scalanie: poziome ciągi + pionowe łączenie wierszy o identycznym wzorze.
    Zwraca listę (kol_od, kol_do, wiersz_od, wiersz_do) w indeksach siatki."""
    wzory = [tuple(runy(w)) for w in g]
    out, i = [], 0
    while i < WYS:
        if not wzory[i]:
            i += 1; continue
        j = i + 1
        # wiersza akcentu (0) nigdy nie scalamy z korpusem — inaczej odstęp
        # akcentu podniósłby też pierwszy wiersz litery
        if i > 0:
            while j < WYS and wzory[j] == wzory[i]:
                j += 1
        for (k0, k1) in wzory[i]:
            out.append((k0, k1, i, j - 1))
        i = j
    return out

# ── odmiany ──────────────────────────────────────────────────────────────────
def prostokaty_zwykle(g, pogrubienie=0):
    for k0, k1, w0, w1 in bloki(g):
        yield (k0 * PX, y_dol(w1), k1 * PX + pogrubienie, y_gora(w0))

def prostokaty_crt(g):
    """każdy piksel osobno: niższy (linia wygaszenia) i rozlany w prawo (poświata)"""
    WYS_PIX, POSWIATA = 184, 64
    for i, wiersz in enumerate(g):
        for (k0, k1) in runy(wiersz):
            dol = y_dol(i)
            yield (k0 * PX, dol, k1 * PX + POSWIATA, dol + WYS_PIX)

ODMIANY = [
    dict(id="Mono-Regular", rodzina="Ogonek 64 Mono", styl="Regular",
         waga=400, bold=False, mono=True, prostokaty=lambda g: prostokaty_zwykle(g, 0)),
    dict(id="Mono-Bold", rodzina="Ogonek 64 Mono", styl="Bold",
         waga=700, bold=True, mono=True, prostokaty=lambda g: prostokaty_zwykle(g, 96)),
    dict(id="Sans-Regular", rodzina="Ogonek 64 Sans", styl="Regular",
         waga=400, bold=False, mono=False, prostokaty=lambda g: prostokaty_zwykle(g, 0)),
    dict(id="CRT-Regular", rodzina="Ogonek 64 CRT", styl="Regular",
         waga=400, bold=False, mono=True, prostokaty=prostokaty_crt),
]

# ── nazwy glifów ─────────────────────────────────────────────────────────────
def nazwa_glifu(cp):
    if cp in UV2AGL:
        return UV2AGL[cp]
    return f"uni{cp:04X}"

def zbierz_glify():
    g = {}
    for plik in ("glify-baza.txt", "glify-dodatki.txt", "glify-pl.txt"):
        for cp, (opis, siatka) in czytaj(os.path.join(KAT, "src", plik)).items():
            if cp in g:
                raise ValueError(f"U+{cp:04X} zdefiniowany dwa razy (ostatni: {plik})")
            g[cp] = siatka
    return g

# ── budowa jednej odmiany ────────────────────────────────────────────────────
def zbuduj(odmiana, glify, katalog):
    mono = odmiana["mono"]
    kolejnosc = [".notdef"] + [nazwa_glifu(cp) for cp in sorted(glify)]
    cmap, kontury, metryki = {}, {}, {}

    # .notdef — ramka 1 px, jak każe konwencja
    pen = TTGlyphPen(None)
    for (x0, y0, x1, y1) in [(PX, 0, 7*PX, PX), (PX, CAP-PX, 7*PX, CAP),
                             (PX, 0, 2*PX, CAP), (6*PX, 0, 7*PX, CAP)]:
        pen.moveTo((x0, y0)); pen.lineTo((x1, y0)); pen.lineTo((x1, y1))
        pen.lineTo((x0, y1)); pen.closePath()
    kontury[".notdef"] = pen.glyph()
    metryki[".notdef"] = (UPM, PX)

    for cp in sorted(glify):
        nazwa = nazwa_glifu(cp)
        siatka = glify[cp]
        prost = list(odmiana["prostokaty"](siatka))
        kolumny = [j for w in siatka for j, c in enumerate(w) if c == "#"]

        if mono or not kolumny:
            dx, advance = 0, UPM
            if not mono:                       # spacja w odmianie proporcjonalnej
                advance = 3 * PX
        else:
            dx = -min(kolumny) * PX            # dosuń do lewej krawędzi
            advance = (max(kolumny) - min(kolumny) + 1) * PX + 2*PX
            # 2 px, nie 1: przy 1 px litery jak ż/ó zlepialy sie w renderze

        pen = TTGlyphPen(None)
        for (x0, y0, x1, y1) in prost:
            x0 += dx; x1 += dx
            pen.moveTo((x0, y0)); pen.lineTo((x1, y0))
            pen.lineTo((x1, y1)); pen.lineTo((x0, y1)); pen.closePath()
        kontury[nazwa] = pen.glyph()
        lsb = (min(kolumny) * PX + dx) if kolumny else 0
        metryki[nazwa] = (advance, lsb)
        cmap[cp] = nazwa

    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(kolejnosc)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(kontury)
    fb.setupHorizontalMetrics(metryki)
    fb.setupHorizontalHeader(ascent=ASCENDER, descent=DESCENDER, lineGap=0)

    pelna = f'{odmiana["rodzina"]} {odmiana["styl"]}'
    ps = pelna.replace(" ", "")
    fb.setupNameTable({
        "copyright":         (f"Copyright (c) {ROK} SMOK - Arek Bronowicki. "
                              "Licencja SIL Open Font License 1.1."),
        "familyName":        odmiana["rodzina"],
        "styleName":         odmiana["styl"],
        "uniqueFontIdentifier": f'{pelna}; wersja {WERSJA}; SMOK',
        "fullName":          pelna,
        "version":           WERSJA,
        "psName":            ps,
        "designer":          "SMOK - Arek Bronowicki",
        "manufacturer":      "SMOK",
        "vendorURL":         "https://github.com/arekbr/ogonek64",
        "designerURL":       "https://github.com/arekbr/ogonek64",
        "description":       ("Pikselowy krój 8x10 z polskimi znakami diakrytycznymi. "
                              "Baza lacinska odwzorowuje krój znakowy Commodore 64; "
                              "diakryty, interpunkcja polska i brakujace znaki ASCII "
                              "zaprojektowane od nowa. Projekt nieoficjalny, "
                              "niezwiazany z wlascicielem marki Commodore."),
        "licenseDescription": ("This Font Software is licensed under the SIL Open Font "
                              "License, Version 1.1. This license is available with a FAQ at "
                              "https://openfontlicense.org"),
        "licenseInfoURL":    "https://openfontlicense.org",
        "sampleText":        "Zazolc gesla jazn — ZAZOLC GESLA JAZN",
    })
    fb.setupOS2(
        sTypoAscender=ASCENDER, sTypoDescender=DESCENDER, sTypoLineGap=0,
        usWinAscent=ASCENDER, usWinDescent=-DESCENDER,
        sCapHeight=CAP, sxHeight=XHEIGHT,
        usWeightClass=odmiana["waga"], usWidthClass=5,
        fsType=0,                                   # bez ograniczeń osadzania
        fsSelection=(1 << 5) if odmiana["bold"] else (1 << 6),   # BOLD albo REGULAR
        achVendID="OGNK",
        panose=dict(bFamilyType=2, bSerifStyle=11,
                    bWeight=8 if odmiana["bold"] else 5, bProportion=9 if mono else 3,
                    bContrast=0, bStrokeVariation=0, bArmStyle=0,
                    bLetterForm=0, bMidline=0, bXHeight=0),
    )
    fb.setupPost(isFixedPitch=1 if mono else 0)
    fb.font["head"].macStyle = 1 if odmiana["bold"] else 0
    fb.setupDummyDSIG()

    sciezka = os.path.join(katalog, f"Ogonek64-{odmiana['id']}.ttf")
    fb.save(sciezka)

    # scalenie stykających się prostokątów w jeden kontur
    f = TTFont(sciezka)
    removeOverlaps(f)
    f.save(sciezka)
    return sciezka, len(cmap)

def main():
    glify = zbierz_glify()
    kat = os.path.join(KAT, "build" if ODSTEP_AKCENTU else "build-ciasny")
    os.makedirs(kat, exist_ok=True)
    print(f"glify wejściowe: {len(glify)}")
    print(f"UPM {UPM} · piksel {PX} · ascender {ASCENDER} · descender {DESCENDER} "
          f"· capHeight {CAP} · xHeight {XHEIGHT}")
    print(f"odstęp akcentu: {ODSTEP_AKCENTU} jednostek "
          f"({ODSTEP_AKCENTU // PX} px) · wysokość całkowita "
          f"{(ASCENDER - DESCENDER) // PX} px · interlinia "
          f"{(ASCENDER - DESCENDER) / UPM:.3f} em")
    print()
    for od in ODMIANY:
        sciezka, ile = zbuduj(od, glify, kat)
        rozmiar = os.path.getsize(sciezka)
        print(f"  ✓ {os.path.basename(sciezka):32} {ile:3} znaków  {rozmiar:6} B  "
              f"[{od['rodzina']} {od['styl']}]")
    print(f"\nwynik w {os.path.relpath(kat, KAT)}/")

if __name__ == "__main__":
    main()
