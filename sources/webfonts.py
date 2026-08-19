#!/usr/bin/env python3
"""ogonek64 — kompresja gotowych TTF do WOFF2 (fonts/ttf -> fonts/webfonts).

Osobny krok, bo WOFF2 to wyłącznie opakowanie: te same glify, ta sama tablica
`cmap`, tylko ciaśniej upakowane. Budowa fontu należy do `buduj.py`.
"""
import os, sys
from fontTools.ttLib import TTFont

KAT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZRODLO = os.path.join(KAT, "fonts", "ttf")
CEL = os.path.join(KAT, "fonts", "webfonts")


def main():
    if not os.path.isdir(ZRODLO):
        print(f"BRAK katalogu {ZRODLO} — najpierw ./build.sh", file=sys.stderr)
        return 1
    pliki = sorted(f for f in os.listdir(ZRODLO) if f.endswith(".ttf"))
    if not pliki:
        print(f"BRAK plików .ttf w {ZRODLO} — najpierw ./build.sh", file=sys.stderr)
        return 1
    os.makedirs(CEL, exist_ok=True)
    for nazwa in pliki:
        wej = os.path.join(ZRODLO, nazwa)
        wyj = os.path.join(CEL, nazwa[:-4] + ".woff2")
        f = TTFont(wej)
        f.flavor = "woff2"
        f.save(wyj)
        przed, po = os.path.getsize(wej), os.path.getsize(wyj)
        print(f"  ✓ {os.path.basename(wyj):32} {przed:6} → {po:6} B  "
              f"(−{100 - po * 100 // przed}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
