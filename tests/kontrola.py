#!/usr/bin/env python3
"""ogonek64 — kontrola zbudowanych fontów. Sprawdza cmap, metryki i RENDERUJE.

Zwrotka „font zbudowany" nic nie dowodzi — dowodem jest obraz i odczyt tabel.
"""
import os, sys
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

KAT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(KAT, "build")

POLSKIE = "ĄĆĘŁŃÓŚŹŻąćęłńóśźż"
ASCII_WYM = "".join(chr(c) for c in range(0x20, 0x7F))
PROBKI = [
    "Zażółć gęślą jaźń",
    "ZAŻÓŁĆ GĘŚLĄ JAŹŃ",
    "Ą Ć Ę Ł Ń Ó Ś Ź Ż",
    "ą ć ę ł ń ó ś ź ż",
    "Ź vs Ż   ź vs ż",
    "Pchnąć w tę łódź jeża",
    "0123456789 !@#$%&*()",
    "{|}~ \\^_` [] <> +=-",
]

def sprawdz_tabele(sciezka):
    f = TTFont(sciezka)
    cmap = f.getBestCmap()
    braki_pl = [c for c in POLSKIE if ord(c) not in cmap]
    braki_ascii = [c for c in ASCII_WYM if ord(c) not in cmap]
    hmtx = f["hmtx"].metrics
    mono = f["post"].isFixedPitch
    adv = {a for a, _ in hmtx.values()}
    os2, head, hhea = f["OS/2"], f["head"], f["hhea"]
    wynik = dict(
        nazwa=f"{f['name'].getDebugName(1)} {f['name'].getDebugName(2)}",
        glifow=len(f.getGlyphOrder()), znakow=len(cmap),
        braki_pl=braki_pl, braki_ascii=braki_ascii,
        mono=bool(mono), unikalnych_advance=len(adv),
        upm=head.unitsPerEm, asc=os2.sTypoAscender, desc=os2.sTypoDescender,
        cap=os2.sCapHeight, xh=os2.sxHeight,
        hhea_asc=hhea.ascent, hhea_desc=hhea.descent,
        waga=os2.usWeightClass, fsType=os2.fsType,
        licencja=(f["name"].getDebugName(14) or "")[:40],
        konturow=sum(len(f["glyf"][g].getCoordinates(f["glyf"])[0])
                     for g in f.getGlyphOrder() if f["glyf"][g].numberOfContours > 0),
    )
    f.close()
    return wynik

def main():
    pliki = sorted(p for p in os.listdir(BUILD) if p.endswith(".ttf"))
    if not pliki:
        print("BRAK plików .ttf w build/ — najpierw lib/buduj.py"); return 1

    print("=" * 78)
    print("KONTROLA TABEL")
    print("=" * 78)
    blad = False
    for p in pliki:
        w = sprawdz_tabele(os.path.join(BUILD, p))
        print(f"\n{p}   [{w['nazwa']}]")
        print(f"  glifów {w['glifow']} · znaków w cmap {w['znakow']} · punktów konturu {w['konturow']}")
        print(f"  UPM {w['upm']} · typo asc/desc {w['asc']}/{w['desc']} · "
              f"hhea {w['hhea_asc']}/{w['hhea_desc']} · cap {w['cap']} · x-height {w['xh']}")
        print(f"  waga {w['waga']} · fsType {w['fsType']} (0 = bez ograniczeń osadzania) · "
              f"isFixedPitch {w['mono']} · różnych szerokości: {w['unikalnych_advance']}")
        print(f"  licencja: {w['licencja']}")
        ok_pl = "✓ 18/18" if not w["braki_pl"] else f"✗ BRAK: {''.join(w['braki_pl'])}"
        ok_as = "✓ 95/95" if not w["braki_ascii"] else f"✗ BRAK: {''.join(w['braki_ascii'])}"
        print(f"  polskie znaki: {ok_pl}    ASCII 0x20-0x7E: {ok_as}")
        if w["braki_pl"] or w["braki_ascii"]:
            blad = True
        if w["mono"] and w["unikalnych_advance"] != 1:
            print(f"  ✗ font mono, a ma {w['unikalnych_advance']} różnych szerokości!")
            blad = True

    # ── RENDER ────────────────────────────────────────────────────────────────
    ROZM, MARG = 40, 24
    for p in pliki:
        font = ImageFont.truetype(os.path.join(BUILD, p), ROZM)
        interlinia = int(ROZM * 1.25) + 6
        wys = MARG * 2 + interlinia * (len(PROBKI) + 1)
        szer = 760
        img = Image.new("RGB", (szer, wys), (32, 40, 96))       # tło jak C64
        d = ImageDraw.Draw(img)
        d.text((MARG, MARG // 2), p.replace(".ttf", ""), font=font, fill=(150, 160, 220))
        for i, t in enumerate(PROBKI):
            d.text((MARG, MARG + interlinia * (i + 1)), t, font=font, fill=(134, 148, 255))
        out = os.path.join(BUILD, p.replace(".ttf", ".png"))
        img.save(out)
        print(f"\nrender: {os.path.relpath(out, KAT)}  ({img.width}x{img.height})")

    # zestawienie wszystkich odmian na jednym obrazie
    linie = []
    for p in pliki:
        linie.append((p.replace("Ogonek64-", "").replace(".ttf", ""),
                      ImageFont.truetype(os.path.join(BUILD, p), ROZM)))
    interlinia = int(ROZM * 1.25) + 10
    img = Image.new("RGB", (860, MARG * 2 + interlinia * len(linie) * 2), (32, 40, 96))
    d = ImageDraw.Draw(img)
    y = MARG
    for nazwa, f in linie:
        d.text((MARG, y), f"— {nazwa}", font=linie[0][1], fill=(110, 120, 190))
        y += interlinia
        d.text((MARG, y), "Zażółć gęślą jaźń ĄĘŁŃŚŹŻ", font=f, fill=(134, 148, 255))
        y += interlinia
    zest = os.path.join(BUILD, "porownanie-odmian.png")
    img.save(zest)
    print(f"render zbiorczy: {os.path.relpath(zest, KAT)}")

    print("\n" + ("✗ SĄ BŁĘDY — patrz wyżej" if blad else "✓ kontrola tabel bez zarzutu"))
    return 1 if blad else 0

if __name__ == "__main__":
    sys.exit(main())
