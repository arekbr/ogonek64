#!/usr/bin/env python3
"""ogonek64 — generator fontów TrueType z tekstowego źródła glifów.

Czyta sources/glify-{baza,dodatki,pl}.txt i buduje rodziny:

  Ogonek 64 Mono   Regular / Bold   stała szerokość, do terminala i kodu
  Ogonek 64 Sans   Regular          szerokość liczona per litera
  Ogonek 64 CRT    Regular          linie wygaszenia + poświata kineskopu

── GEOMETRIA ────────────────────────────────────────────────────────────────
unitsPerEm 2048, 1 piksel = 256 jednostek, komórka 8 x 10 pikseli.
Linia bazowa leży pod wierszem 7 (spód wielkiej litery). Wiersz źródłowy `i`
zajmuje y od (7-i)*256 do (8-i)*256, więc:

  wiersze 0,1   2560 .. 2048   akcent (dwa wiersze)       -> ascender  2560
  wiersz 2      2048 .. 1792   odstęp akcentu
  wiersze 3..9  1792 ..    0   korpus                     -> capHeight 1792
  wiersz 10        0 ..  -256  descender (g j p q y)
  wiersz 11     -256 ..  -512  dolny wiersz ogonka        -> descender -512

Wysokość całkowita 3072 = 12 px = interlinia 1.5 em. To cena za komplet akcentów
europejskich: w jednym wierszu nie da się odróżnić daszka od haczka ani od łuku.

Piksele NIE są zapisywane jako osobne prostokąty — najpierw scalam je w poziome
ciągi, potem w pionowe bloki, a na końcu `removeOverlaps` (skia-pathops) zlepia
je w jeden czysty kontur na glif. Bez tego font miałby setki stykających się
krawędzi, na których rasteryzery robią artefakty.
"""
import os, sys, re, unicodedata
from datetime import datetime, timezone

KAT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KAT, "lib"))
from zrob_glify import czytaj, SZER, WYS

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import ttProgram
from fontTools.ttLib.removeOverlaps import removeOverlaps
from fontTools.agl import UV2AGL

PX        = 256                 # jednostek na piksel
UPM       = SZER * PX           # 2048
BASELINE  = 9                   # wiersz, pod którym leży linia bazowa

# Siatka 8x12: dwa wiersze akcentu, wiersz odstępu, siedem wierszy korpusu, dwa
# wiersze pod linią bazową. Odstęp akcentu jest teraz JAWNY w plikach źródłowych
# (wiersz 2), a nie dokładany przez generator — wcześniejszy parametr OGONEK_ODSTEP
# podnosił pojedynczy wiersz i nie dałby się rozciągnąć na akcenty dwuwierszowe.
ASCENDER  = 2560                # wiersz 0 sięga 10 px nad linię bazową
DESCENDER = -512
CAP       = 1792
XHEIGHT   = 1280
WERSJA    = "1.003"
ROK       = 2026

# ── geometria ────────────────────────────────────────────────────────────────
def y_gora(i):  return (BASELINE + 1 - i) * PX
def y_dol(i):   return (BASELINE - i) * PX

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
    for plik in ("glify-baza.txt", "glify-dodatki.txt", "glify-pl.txt", "glify-latin.txt"):
        for cp, (opis, siatka) in czytaj(os.path.join(KAT, "sources", plik)).items():
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
        pen.moveTo((x0, y0)); pen.lineTo((x0, y1)); pen.lineTo((x1, y1))
        pen.lineTo((x1, y0)); pen.closePath()
    kontury[".notdef"] = pen.glyph()
    metryki[".notdef"] = (UPM, PX)

    for cp in sorted(glify):
        nazwa = nazwa_glifu(cp)
        siatka = glify[cp]
        prost = list(odmiana["prostokaty"](siatka))
        kolumny = [j for w in siatka for j, c in enumerate(w) if c == "#"]

        # 🔴 Akcenty składające (kategoria Unicode Mn) MUSZĄ mieć zerową szerokość,
        #    także w foncie o stałej szerokości — inaczej „a" + combining acute
        #    zajmuje dwie komórki zamiast jednej.
        if unicodedata.category(chr(cp)) == "Mn":
            pen = TTGlyphPen(None)
            for (x0, y0, x1, y1) in prost:
                pen.moveTo((x0, y0)); pen.lineTo((x0, y1))
                pen.lineTo((x1, y1)); pen.lineTo((x1, y0)); pen.closePath()
            kontury[nazwa] = pen.glyph()
            metryki[nazwa] = (0, 0)
            cmap[cp] = nazwa
            continue

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
            # 🔴 Kolejność wierzchołków = KIERUNEK konturu. TrueType wymaga, by kontur
            #    zewnętrzny biegł zgodnie z ruchem wskazówek zegara (przy osi y w górę),
            #    czyli lewy-dolny -> lewy-górny -> prawy-górny -> prawy-dolny.
            #    Odwrotna kolejność daje FAIL `outline_direction [ccw-outer-contour]`.
            pen.moveTo((x0, y0)); pen.lineTo((x0, y1))
            pen.lineTo((x1, y1)); pen.lineTo((x1, y0)); pen.closePath()
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
    # 🔴 PostScript name musi brzmieć "Rodzina-Styl" (z myślnikiem), a nie
    #    "RodzinaStyl" — Google Fonts porównuje go z nazwą pliku.
    ps = odmiana["rodzina"].replace(" ", "") + "-" + odmiana["styl"]
    fb.setupNameTable({
        # 🔴 Google Fonts wymusza dokładnie ten wzór (kontrola googlefonts/font_copyright):
        #    "Copyright RRRR The <Rodzina> Project Authors (adres repozytorium git)".
        #    Nazwa autora nie zmieści się tutaj, dlatego SMOK siedzi w polach
        #    `designer` i `manufacturer` oraz w AUTHORS.txt.
        "copyright":         (f"Copyright {ROK} The {odmiana['rodzina']} Project Authors "
                              "(https://github.com/arekbr/ogonek64)"),
        "familyName":        odmiana["rodzina"],
        "styleName":         odmiana["styl"],
        "uniqueFontIdentifier": f'{WERSJA};OGNK;{ps}',
        "fullName":          pelna,
        "version":           f"Version {WERSJA}",
        "psName":            ps,
        "designer":          "SMOK - Arek Bronowicki",
        "manufacturer":      "SMOK",
        "vendorURL":         "https://github.com/arekbr/ogonek64",
        "designerURL":       "https://github.com/arekbr/ogonek64",
        "description":       ("Pixel typeface on an 8x12 grid with full Polish diacritics "
                              "and GF Latin Core coverage."),
        # 🔴 Dwukropek po "FAQ at" jest OBOWIĄZKOWY — kontrola googlefonts/name/license
        #    porównuje ten napis znak w znak.
        "licenseDescription": ("This Font Software is licensed under the SIL Open Font "
                              "License, Version 1.1. This license is available with a FAQ "
                              "at: https://openfontlicense.org"),
        "licenseInfoURL":    "https://openfontlicense.org",
        "sampleText":        "Zazolc gesla jazn — ZAZOLC GESLA JAZN",
    })
    fb.setupOS2(
        sTypoAscender=ASCENDER, sTypoDescender=DESCENDER, sTypoLineGap=0,
        usWinAscent=ASCENDER, usWinDescent=-DESCENDER,
        sCapHeight=CAP, sxHeight=XHEIGHT,
        usWeightClass=odmiana["waga"], usWidthClass=5,
        fsType=0,                                   # bez ograniczeń osadzania
        # bit 5 = BOLD, bit 6 = REGULAR, bit 7 = USE_TYPO_METRICS (wymagany przez GF,
        # każe programom brać wysokości z pól sTypo*, a nie z usWin*)
        fsSelection=((1 << 5) if odmiana["bold"] else (1 << 6)) | (1 << 7),
        achVendID="OGNK",
        panose=dict(bFamilyType=2, bSerifStyle=11,
                    bWeight=8 if odmiana["bold"] else 5, bProportion=9 if mono else 3,
                    bContrast=0, bStrokeVariation=0, bArmStyle=0,
                    bLetterForm=0, bMidline=0, bXHeight=0),
    )
    fb.setupPost(isFixedPitch=1 if mono else 0)
    fb.font["head"].macStyle = 1 if odmiana["bold"] else 0

    # head.fontRevision MUSI zgadzać się z nameID 5, inaczej różne programy pokazują
    # różne numery wersji (kontrola opentype/font_version)
    fb.font["head"].fontRevision = float(WERSJA)

    # 🔴 fsSelection bity 7-9 istnieją dopiero od OS/2 w wersji 4. Ustawienie bitu 7
    #    (USE_TYPO_METRICS) przy starszej wersji tablicy sypie kontrolę ttx_roundtrip.
    fb.font["OS/2"].version = 4

    # Tabela `meta` z deklaracja jezykow/pism (WARN googlefonts/meta/script_lang_tags)
    meta = newTable("meta")
    meta.data = {"dlng": "Latn", "slng": "Latn"}
    fb.font["meta"] = meta

    # Strony kodowe w OS/2: bit 0 = Latin 1, bit 1 = Latin 2 (Europa Środkowa).
    # Bez tego kontrola opentype/code_pages daje FAIL.
    fb.font["OS/2"].ulCodePageRange1 = (1 << 0) | (1 << 1)
    fb.font["OS/2"].ulCodePageRange2 = 0

    # gasp — sterowanie wygładzaniem. Font pikselowy nie chce antyaliasu w małych
    # rozmiarach, ale tablica musi istnieć (kontrola googlefonts/gasp).
    gasp = newTable("gasp")
    gasp.version = 1
    gasp.gaspRange = {65535: 15}
    fb.font["gasp"] = gasp

    # prep — „smart dropout control”. Zapobiega gubieniu cienkich elementów przy
    # rasteryzacji w małych rozmiarach (kontrola smart_dropout).
    prep = newTable("prep")
    prep.program = ttProgram.Program()
    prep.program.fromAssembly(["PUSHW[]", "511", "SCANCTRL[]", "PUSHB[]", "4", "SCANTYPE[]"])
    fb.font["prep"] = prep

    # DSIG jest przez Google Fonts uznany za zbędny (WARN found-DSIG) — nie dodajemy.

    # 🔴 Konwencja Google Fonts: "FamilyName-Style.ttf", rodzina BEZ spacji i bez
    #    dodatkowych myślników. "Ogonek 64 Mono" + "Regular" -> Ogonek64Mono-Regular.ttf
    #    (nie Ogonek64-Mono-Regular.ttf, jak było wcześniej).
    nazwa_pliku = odmiana["rodzina"].replace(" ", "") + "-" + odmiana["styl"] + ".ttf"
    sciezka = os.path.join(katalog, nazwa_pliku)
    fb.save(sciezka)

    # scalenie stykających się prostokątów w jeden kontur
    f = TTFont(sciezka)
    removeOverlaps(f)
    f.save(sciezka)
    return sciezka, len(cmap)

def main():
    glify = zbierz_glify()
    kat = os.path.join(KAT, "fonts", "ttf")
    os.makedirs(kat, exist_ok=True)
    print(f"glify wejściowe: {len(glify)}")
    print(f"UPM {UPM} · piksel {PX} · ascender {ASCENDER} · descender {DESCENDER} "
          f"· capHeight {CAP} · xHeight {XHEIGHT}")
    print(f"siatka {SZER}x{WYS} · wysokość całkowita {(ASCENDER - DESCENDER) // PX} px "
          f"· interlinia {(ASCENDER - DESCENDER) / UPM:.3f} em")
    print()
    for od in ODMIANY:
        sciezka, ile = zbuduj(od, glify, kat)
        rozmiar = os.path.getsize(sciezka)
        print(f"  ✓ {os.path.basename(sciezka):32} {ile:3} znaków  {rozmiar:6} B  "
              f"[{od['rodzina']} {od['styl']}]")
    print(f"\nwynik w {os.path.relpath(kat, KAT)}/")

if __name__ == "__main__":
    main()
