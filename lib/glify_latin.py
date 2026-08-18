#!/usr/bin/env python3
"""ogonek64 — rozszerzenie do GF Latin Core (319 znaków).

Google Fonts wymaga minimum zestawu `GF_Latin_Core`. Ten moduł dokłada brakujące
197 znaków do bazowych 124 i zapisuje je jako `src/glify-latin.txt`.

Podział pracy:
  * 143 litery z akcentem  -> SKŁADANE AUTOMATYCZNIE z rozkładu Unicode
                              (`unicodedata.decomposition` daje bazę + akcent)
  *  22 litery bez rozkładu -> rysowane ręcznie (Æ Ð Ø Þ ß Œ ı Ħ …)
  *  20 symboli i walut     -> rysowane ręcznie (€ © ® ™ × ÷ °…)
  *  14 akcentów składających (combining) -> te same wzory, ZEROWA szerokość
  *  12 znaków interpunkcji -> rysowane ręcznie (¡ ¿ « » § ¶ •…)

── DLACZEGO AKCENTY MAJĄ DWA WIERSZE ───────────────────────────────────────────
W jednym wierszu 8 pikseli `ˆ ˇ ˘ ˚ ¨ ˜ ˝` są nierozróżnialne — wszystkie stają się
tą samą plamką. To ta sama pułapka, co przy `Ź`/`Ż`, gdzie różnica jednego piksela
w pozycji okazała się niewidoczna. Dlatego siatka ma 12 wierszy: dwa na akcent,
jeden na odstęp, siedem na korpus, dwa pod linię bazową.

Pozycje akcentu zależą od wysokości litery:
  WIELKIE (korpus 3..9)   akcent dwuwierszowy w 0..1, jednowierszowy w 1, odstęp 2
  MAŁE    (x-height 5..9) akcent dwuwierszowy w 2..3, jednowierszowy w 3, odstęp 4
Akcenty pod literą (cedilla, przecinek, ogonek) siedzą w 10..11 niezależnie od
wielkości, bo linia bazowa jest wspólna.
"""
import os, sys, unicodedata
from collections import defaultdict

KAT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KAT, "lib"))
from zrob_glify import czytaj, pusty, naloz, wzor, odbij, zakres_kolumn, trzon, SZER, WYS

# ── AKCENTY: (górny wiersz, dolny wiersz) dla WIELKIEJ litery ────────────────
# None w górnym = akcent jednowierszowy (siedzi tylko w dolnym, bliżej litery)
AKCENTY_NAD = {
    0x0300: (".##.....", "..##...."),   # ̀  grave      — ukos w lewo
    0x0301: (".....##.", "....##.."),   # ́  acute      — ukos w prawo
    0x0302: ("...##...", ".##..##."),   # ̂  circumflex — daszek
    0x0303: (".###....", "...####."),   # ̃  tilde      — fala (ciągła, jak nasza ~)
    0x0304: (None,       ".######."),   # ̄  macron     — pełna kreska
    0x0306: (".#....#.", "..####.."),   # ̆  breve      — łuk otwarty w górę
    0x0307: (None,       "...##..."),   # ̇  dot above
    0x0308: (None,       ".##..##."),   # ̈  diaeresis  — dwie kropki
    0x030A: ("..####..", "..#..#.."),   # ̊  ring above
    0x030B: ("..#..##.", ".##..#.."),   # ̋  double acute — dwa ukosy
    0x030C: (".##..##.", "...##..."),   # ̌  caron      — odwrócony daszek
}
# ── AKCENTY POD LITERĄ: (wiersz 10, wiersz 11) ──────────────────────────────
AKCENTY_POD = {
    0x0327: ("....##..", "..###..."),   # ̧  cedilla    — haczyk w lewo
    0x0326: ("...##...", "..##...."),   # ̦  comma below — prosty ukos
}
# ogonek jest zależny od szerokości litery, więc liczony osobno (patrz `ogonek_pod`)
OGONEK = 0x0328

WIERSZ_ODSTEPU_DUZE = 2
WIERSZ_ODSTEPU_MALE = 4

def gorna_krawedz(siatka):
    """pierwszy niepusty wiersz litery"""
    for i, w in enumerate(siatka):
        if "#" in w:
            return i
    return WYS

def akcent_nad(kod_akcentu, siatka):
    """Umieszcza akcent WZGLĘDEM FAKTYCZNEJ górnej krawędzi litery, a nie według
    sztywnego podziału na wielkie i małe.

    🔴 Sztywne pozycje (0..1 dla wielkich, 2..3 dla małych) wywracały się na 13
    znakach: `i` ma kropkę wyżej niż x-height, a `d k l t` mają wznoszące. Akcent
    wjeżdżał wtedy w literę albo w wiersz odstępu. Liczone od krawędzi działa dla
    wszystkich trzech wysokości bez wyjątków:

        wielkie (krawędź 3)      -> akcent 0..1, odstęp 2
        wznoszące (krawędź 4)    -> akcent 1..2, odstęp 3
        x-height (krawędź 5)     -> akcent 2..3, odstęp 4
    """
    gora, dol = AKCENTY_NAD[kod_akcentu]
    k = gorna_krawedz(siatka)
    g = pusty()
    if gora is not None:
        if k - 3 < 0:
            raise ValueError(f"brak miejsca na akcent dwuwierszowy (krawedz {k})")
        g[k - 3] = gora
        g[k - 2] = dol
    else:
        if k - 2 < 0:
            raise ValueError(f"brak miejsca na akcent (krawedz {k})")
        g[k - 2] = dol
    return g

def ogonek_pod(siatka):
    """ogonek zaczepiony pod PRAWĄ krawędzią litery"""
    l, p = zakres_kolumn(siatka)
    kol = max(p - 1, 1)
    g = pusty()
    g[10] = "".join("#" if i in (kol, kol + 1) else "." for i in range(SZER))
    g[11] = "".join("#" if i in (kol - 1, kol) else "." for i in range(SZER))
    return g

def akcent_pod(kod_akcentu, siatka):
    if kod_akcentu == OGONEK:
        return ogonek_pod(siatka)
    a, b = AKCENTY_POD[kod_akcentu]
    g = pusty()
    g[10] = a
    g[11] = b
    return g

def zloz(baza_siatka, kody_akcentow):
    """nakłada akcenty na literę bazową; zwraca (siatka, ostrzeżenia)"""
    ostrz = []
    nad = [k for k in kody_akcentow if k in AKCENTY_NAD]
    pod = [k for k in kody_akcentow if k in AKCENTY_POD or k == OGONEK]
    obce = [k for k in kody_akcentow if k not in AKCENTY_NAD and k not in AKCENTY_POD and k != OGONEK]
    for k in obce:
        ostrz.append(f"nieznany akcent U+{k:04X}")

    wynik = list(baza_siatka)
    # 🔴 Akcent nad `i`/`j` ZASTĘPUJE kropkę — tak działa typografia (í, ï, ĭ).
    #    Bez tego kropka i akcent zderzają się w jednym miejscu.
    if nad:
        wynik = bez_kropki(wynik)
    for ka in nad:
        wynik = naloz(wynik, akcent_nad(ka, wynik))
    # akcenty pod literą nie dotyczą górnego odstępu, więc liczone z ORYGINAŁU
    for ka in pod:
        wynik = naloz(wynik, akcent_pod(ka, baza_siatka))
    return wynik, ostrz

# ══ TRANSFORMACJE — taniej niż rysowanie od zera ═══════════════════════════════
def kreska_pozioma(siatka, wiersz, od, do):
    """pozioma kreska przez literę: Đ, Ħ, ħ, ¢, €, ¥"""
    out = list(siatka)
    linia = "".join("#" if od <= i <= do else "." for i in range(SZER))
    out[wiersz] = "".join("#" if a == "#" or b == "#" else "."
                          for a, b in zip(out[wiersz], linia))
    return out

def ukos_przez(siatka):
    """przekreślenie ukośne od dolnego-lewa do górnego-prawa: Ø, ø"""
    l, p = zakres_kolumn(siatka)
    wiersze = [i for i, w in enumerate(siatka) if "#" in w]
    if not wiersze:
        return siatka
    g, d = wiersze[0], wiersze[-1]
    out = list(siatka)
    n = d - g + 1
    for k in range(n):
        i = d - k
        kol = l + int(round(k * (p - l) / max(n - 1, 1)))
        out[i] = "".join("#" if a == "#" or j == kol else "."
                         for j, a in enumerate(out[i]))
    return out

def bez_kropki(siatka):
    """usuwa kropkę nad literą: ı z i, ȷ z j.
    Kropka to najwyższy niepusty wiersz ODDZIELONY od korpusu pustym wierszem."""
    out = list(siatka)
    niepuste = [i for i, w in enumerate(out) if "#" in w]
    if len(niepuste) < 3:
        return out
    pierwszy = niepuste[0]
    if out[pierwszy + 1] == "." * SZER:      # jest przerwa => to kropka
        out[pierwszy] = "." * SZER
    return out

def jako_znak(wzorzec_akcentu):
    """akcent jako SAMODZIELNY znak (´ ¨ ˆ ˇ ˜ ¯ ˘ ˙ ˚ ˝).

    🔴 Siedzi DOKŁADNIE tam, gdzie akcent nad wielką literą (wiersze 0-1). Pierwsza
    wersja opuszczała go do połowy wysokości litery „żeby nie wisiał w pustce" — to był
    błąd: `´` obok `Á` musi być na tej samej wysokości, inaczej wygląda jak inny znak.
    Wychwycone dopiero na arkuszu wszystkich glifów, nie przez kontrolę tabel.
    """
    gora, dol = wzorzec_akcentu
    g = pusty()
    if gora is not None:
        g[0] = gora
        g[1] = dol
    else:
        g[1] = dol
    return g

# ══ GLIFY RYSOWANE OD ZERA ════════════════════════════════════════════════════
# Tylko te, których nie da się złożyć z istniejących. Korpus wielkich = 3..9,
# małych = 5..9.
RYSOWANE = {
0x00C6: ("LATIN CAPITAL LETTER AE", dict(
    w3="..######", w4=".##.##..", w5=".##.##..", w6=".#####..",
    w7="##..##..", w8="##..##..", w9="##..####")),
0x00E6: ("LATIN SMALL LETTER AE", dict(
    w5="..##.##.", w6=".##.##..", w7=".######.", w8="##..##..", w9=".##.####")),
0x0152: ("LATIN CAPITAL LIGATURE OE", dict(
    w3="..######", w4=".##.##..", w5="##..##..", w6="##..####",
    w7="##..##..", w8=".##.##..", w9="..######")),
0x0153: ("LATIN SMALL LIGATURE OE", dict(
    w5="..##.##.", w6=".##.##..", w7=".##.####", w8=".##.##..", w9="..##.###")),
0x00D0: ("LATIN CAPITAL LETTER ETH", dict(
    w3=".#####..", w4=".##..##.", w5=".##..##.", w6="####.##.",
    w7=".##..##.", w8=".##..##.", w9=".#####..")),
0x00F0: ("LATIN SMALL LETTER ETH", dict(
    w3="..##.##.", w4="...###..", w5="..####..", w6=".##..##.",
    w7=".##..##.", w8=".##..##.", w9="..####..")),
0x00DE: ("LATIN CAPITAL LETTER THORN", dict(
    w3=".##.....", w4=".#####..", w5=".##..##.", w6=".##..##.",
    w7=".#####..", w8=".##.....", w9=".##.....")),
0x00FE: ("LATIN SMALL LETTER THORN", dict(
    w3=".##.....", w4=".##.....", w5=".#####..", w6=".##..##.",
    w7=".##..##.", w8=".#####..", w9=".##.....", w10=".##.....")),
0x00DF: ("LATIN SMALL LETTER SHARP S", dict(
    w3="..####..", w4=".##..##.", w5=".##.....", w6=".#####..",
    w7=".##..##.", w8=".##..##.", w9=".##.###.")),
0x1E9E: ("LATIN CAPITAL LETTER SHARP S", dict(
    w3=".#####..", w4=".##..##.", w5=".##..##.", w6=".#####..",
    w7=".##...##", w8=".##...##", w9=".##.####")),
0x00AA: ("FEMININE ORDINAL INDICATOR", dict(
    w3="..####..", w4=".....##.", w5="..#####.", w6=".##..##.",
    w7="..#####.", w8="..#####.")),
0x00BA: ("MASCULINE ORDINAL INDICATOR", dict(
    w3="..####..", w4=".##..##.", w5=".##..##.", w6=".##..##.",
    w7="..####..", w8="..#####.")),
# ── symbole ──
0x00A2: ("CENT SIGN", dict(
    w4="....##..", w5="..#####.", w6=".##.....", w7=".##.....",
    w8="..#####.", w9="...##...")),
0x00A5: ("YEN SIGN", dict(
    w3=".##..##.", w4=".##..##.", w5="..####..", w6=".######.",
    w7="...##...", w8=".######.", w9="...##...")),
0x00A9: ("COPYRIGHT SIGN", dict(
    w3="..####..", w4=".##..##.", w5="##.##.##", w6="##.#...#",
    w7="##.##.##", w8=".##..##.", w9="..####..")),
0x00AE: ("REGISTERED SIGN", dict(
    w3="..####..", w4=".##..##.", w5="##.##.##", w6="##.##.##",
    w7="##.###.#", w8=".##.#.##", w9="..####..")),
0x00B0: ("DEGREE SIGN", dict(
    w3="..####..", w4=".##..##.", w5="..####..")),
0x00D7: ("MULTIPLICATION SIGN", dict(
    w5=".##..##.", w6="..####..", w7="...##...", w8="..####..", w9=".##..##.")),
0x00F7: ("DIVISION SIGN", dict(
    w4="...##...", w6=".######.", w8="...##...")),
0x20AC: ("EURO SIGN", dict(
    w3="..#####.", w4=".##.....", w5="######..", w6=".##.....",
    w7="######..", w8=".##.....", w9="..#####.")),
0x2122: ("TRADE MARK SIGN", dict(
    w3="#####.#.", w4="..#..###", w5="..#..#.#")),
0x2212: ("MINUS SIGN", dict(w6=".######.")),
# ── interpunkcja ──
0x00A7: ("SECTION SIGN", dict(
    w3="..####..", w4=".##..##.", w5="..###...", w6=".##.##..",
    w7="...###..", w8=".##..##.", w9="..####..")),
0x00B6: ("PILCROW SIGN", dict(
    w3="..######", w4=".####.##", w5=".####.##", w6="..###.##",
    w7="....#.##", w8="....#.##", w9="....#.##")),
0x00B7: ("MIDDLE DOT", dict(w6="...##...")),
0x2022: ("BULLET", dict(w5="..####..", w6="..####..", w7="..####..")),
0x00AB: ("LEFT-POINTING DOUBLE ANGLE QUOTATION MARK", dict(
    w5=".##..##.", w6="##..##..", w7=".##..##.")),
0x2039: ("SINGLE LEFT-POINTING ANGLE QUOTATION MARK", dict(
    w5="...##...", w6="..##....", w7="...##...")),
0x201C: ("LEFT DOUBLE QUOTATION MARK", dict(w3=".#..#...", w4=".##.##..")),
0x2018: ("LEFT SINGLE QUOTATION MARK", dict(w3="...#....", w4="...##...")),
}

def odbij_pion(siatka, od=3, do=9):
    """odbicie w pionie w obrębie korpusu: ¡ z !, ¿ z ?"""
    out = list(siatka)
    fragment = out[od:do+1][::-1]
    out[od:do+1] = fragment
    return out

# ══ TRANSFORMACJE Z ISTNIEJĄCYCH GLIFÓW ═══════════════════════════════════════
# kod -> (nazwa, kod_zrodlowy, funkcja)
POCHODNE = {
0x0110: ("LATIN CAPITAL LETTER D WITH STROKE", 0x0044, lambda g: kreska_pozioma(g, 6, 0, 3)),
0x0111: ("LATIN SMALL LETTER D WITH STROKE",   0x0064, lambda g: kreska_pozioma(g, 4, 2, 5)),
0x0126: ("LATIN CAPITAL LETTER H WITH STROKE", 0x0048, lambda g: kreska_pozioma(g, 3, 0, 7)),
0x0127: ("LATIN SMALL LETTER H WITH STROKE",   0x0068, lambda g: kreska_pozioma(g, 4, 0, 5)),
0x00D8: ("LATIN CAPITAL LETTER O WITH STROKE", 0x004F, ukos_przez),
0x00F8: ("LATIN SMALL LETTER O WITH STROKE",   0x006F, ukos_przez),
0x0131: ("LATIN SMALL LETTER DOTLESS I",       0x0069, bez_kropki),
0x0237: ("LATIN SMALL LETTER DOTLESS J",       0x006A, bez_kropki),
0x00A1: ("INVERTED EXCLAMATION MARK",          0x0021, odbij_pion),
0x00BF: ("INVERTED QUESTION MARK",             0x003F, odbij_pion),
}
# znaki, ktore sa odbiciem w poziomie znaku juz zdefiniowanego w RYSOWANE
POCHODNE_RYSOWANE = {
0x00BB: ("RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK", 0x00AB, odbij),
0x203A: ("SINGLE RIGHT-POINTING ANGLE QUOTATION MARK", 0x2039, odbij),
}
# akcenty jako samodzielne znaki (spacing modifiers)
SAMODZIELNE = {
0x00B4: ("ACUTE ACCENT",        0x0301), 0x00A8: ("DIAERESIS",       0x0308),
0x02C6: ("MODIFIER LETTER CIRCUMFLEX ACCENT", 0x0302),
0x02C7: ("CARON",               0x030C), 0x02DC: ("SMALL TILDE",     0x0303),
0x00AF: ("MACRON",              0x0304), 0x02D8: ("BREVE",           0x0306),
0x02D9: ("DOT ABOVE",           0x0307), 0x02DA: ("RING ABOVE",      0x030A),
0x02DD: ("DOUBLE ACUTE ACCENT", 0x030B),
}
# akcenty pod litera jako samodzielne znaki
SAMODZIELNE_POD = {
0x00B8: ("CEDILLA", 0x0327), 0x02DB: ("OGONEK", 0x0328),
}

def main():
    import glyphsets
    core = set(glyphsets.unicodes_per_glyphset("GF_Latin_Core"))
    istniejace = {}
    for plik in ("glify-baza.txt", "glify-dodatki.txt", "glify-pl.txt"):
        istniejace.update(czytaj(os.path.join(KAT, "src", plik)))

    nowe, powody, nieudane = {}, defaultdict(int), []

    # 1. rysowane od zera
    for kod, (nazwa, kw) in RYSOWANE.items():
        nowe[kod] = (nazwa, wzor(**kw)); powody["rysowane od zera"] += 1
    # 2. odbicia znakow rysowanych
    for kod, (nazwa, zrodlo, fn) in POCHODNE_RYSOWANE.items():
        if zrodlo in nowe:
            nowe[kod] = (nazwa, fn(nowe[zrodlo][1])); powody["odbicie znaku rysowanego"] += 1
    # 3. pochodne z istniejacych liter
    for kod, (nazwa, zrodlo, fn) in POCHODNE.items():
        if zrodlo in istniejace:
            nowe[kod] = (nazwa, fn(istniejace[zrodlo][1])); powody["transformacja litery"] += 1
        else:
            nieudane.append((kod, f"brak zrodla U+{zrodlo:04X}"))
    # 4. akcenty jako samodzielne znaki
    for kod, (nazwa, ka) in SAMODZIELNE.items():
        nowe[kod] = (nazwa, jako_znak(AKCENTY_NAD[ka])); powody["akcent jako znak"] += 1
    for kod, (nazwa, ka) in SAMODZIELNE_POD.items():
        g = pusty()
        if ka == OGONEK:
            g[10] = "...##..."; g[11] = "..##...."
        else:
            g[10], g[11] = AKCENTY_POD[ka]
        # podnosimy do linii bazowej, bo jako samodzielny znak nie wisi pod litera
        nowe[kod] = (nazwa, g); powody["akcent pod jako znak"] += 1
    # 5. akcenty skladajace (combining) — ten sam wzor, advance 0 ustawia generator
    for ka in list(AKCENTY_NAD) + list(AKCENTY_POD) + [OGONEK]:
        if ka not in core:
            continue
        try: nazwa = unicodedata.name(chr(ka))
        except ValueError: nazwa = f"COMBINING U+{ka:04X}"
        if ka in AKCENTY_NAD:
            wzorzec = pusty(); wzorzec[3] = "#" * SZER   # atrapa: krawędź na 3
            nowe[ka] = (nazwa, akcent_nad(ka, wzorzec))
        elif ka == OGONEK:
            g = pusty(); g[10] = "...##..."; g[11] = "..##...."
            nowe[ka] = (nazwa, g)
        else:
            g = pusty(); g[10], g[11] = AKCENTY_POD[ka]
            nowe[ka] = (nazwa, g)
        powody["akcent skladajacy"] += 1

    # 6. GŁÓWNA CZĘŚĆ: litery z akcentem, składane z rozkładu Unicode
    do_zrobienia = sorted(core - set(istniejace) - set(nowe))
    for kod in do_zrobienia:
        ch = chr(kod)
        rozkl = unicodedata.decomposition(ch)
        if not rozkl or rozkl.startswith("<"):
            nieudane.append((kod, "brak rozkladu Unicode")); continue
        czesci = rozkl.split()
        baza_kod = int(czesci[0], 16)
        akcenty = [int(x, 16) for x in czesci[1:]]
        zrodlo = istniejace.get(baza_kod) or nowe.get(baza_kod)
        if not zrodlo:
            nieudane.append((kod, f"brak bazy U+{baza_kod:04X}")); continue
        nieznane = [a for a in akcenty if a not in AKCENTY_NAD and a not in AKCENTY_POD and a != OGONEK]
        if nieznane:
            nieudane.append((kod, "akcent " + " ".join(f"U+{a:04X}" for a in nieznane))); continue
        try:
            siatka, ostrz = zloz(zrodlo[1], akcenty)
        except ValueError as e:
            nieudane.append((kod, str(e))); continue
        try: nazwa = unicodedata.name(ch)
        except ValueError: nazwa = f"U+{kod:04X}"
        nowe[kod] = (nazwa, siatka); powody["skladane z rozkladu Unicode"] += 1

    # ── zapis ──
    out = ["# ogonek64 — GF Latin Core: znaki dolozone do bazowych 124",
           "# siatka 8 x 12 (0,1=akcent · 2=odstep · 3..9=korpus · 10,11=pod baseline)",
           "# Wiekszosc zlozona automatycznie z rozkladu Unicode: baza + akcent.", ""]
    for kod in sorted(nowe):
        nazwa, g = nowe[kod]
        out.append(f"U+{kod:04X} {nazwa}")
        out.extend(g)
        out.append("")
    open(os.path.join(KAT, "src", "glify-latin.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")

    print(f"zapisano src/glify-latin.txt — {len(nowe)} glifow")
    for k, v in sorted(powody.items(), key=lambda x: -x[1]):
        print(f"   {v:4}  {k}")
    razem = set(istniejace) | set(nowe)
    print(f"\nRAZEM w foncie: {len(razem)} znakow")
    brak = sorted(core - razem)
    print(f"BRAK do Latin Core: {len(brak)}")
    if brak:
        for cp in brak[:40]:
            try: n = unicodedata.name(chr(cp))
            except ValueError: n = "?"
            print(f"   U+{cp:04X} {chr(cp)}  {n}")
    if nieudane:
        print(f"\nNIEUDANE ({len(nieudane)}):")
        for kod, powod in nieudane[:25]:
            print(f"   U+{kod:04X} {chr(kod)}  <- {powod}")

if __name__ == "__main__":
    main()
