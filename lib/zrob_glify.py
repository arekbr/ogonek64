#!/usr/bin/env python3
"""ogonek64 — generator glifów dodatkowych i polskich.

Czyta src/glify-baza.txt (baza łacińska), dokłada:
  * 8 znaków ASCII, których C64 nie ma:  \\ ^ _ ` { | } ~
  * 18 polskich diakrytów
  * polską interpunkcję: „ " ‚ ' – — …

Wynik: src/glify-dodatki.txt + src/glify-pl.txt (format czytelny, edytowalny ręcznie).

Siatka 8 x 10, wiersze w kolejności od góry:
  indeks 0 = 'A'  wiersz akcentu nad WIELKĄ literą (jedyny wolny nad korpusem)
  indeks 1..7     korpus ROM (wielkie zajmują 1..7, małe 3..7)
  indeks 8        zejście pod linię bazową (descender: g j p q y; górny wiersz ogonka)
  indeks 9        drugi wiersz zejścia (dolny wiersz ogonka)

Nad MAŁĄ literą wolne są wiersze 1 i 2 — dlatego małe litery dostają akcent
dwuwierszowy (prawdziwy ukos), a wielkie jednowierszowy, płaski. To nie
niekonsekwencja, a standardowa praktyka typograficzna: akcenty nad kapitalikami
są spłaszczane, żeby nie rozpychać interlinii.
"""
import os, sys, re

KAT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SZER, WYS = 8, 10

# ── wczytanie bazy ────────────────────────────────────────────────────────────
WIERSZ_GLIFU = re.compile(r"^[.#]{%d}$" % SZER)
NAGLOWEK     = re.compile(r"^U\+([0-9A-Fa-f]{4,6})\s+(.*)$")

def czytaj(sciezka):
    """Parser formatu źródłowego.

    🔴 MINA: '#' jest JEDNOCZEŚNIE pikselem i znakiem komentarza. Rozpoznawanie
    komentarza po `startswith('#')` zjadało wiersze glifów z zapalonym pikselem
    w kolumnie 0 — U+0023 '#' tracił 2 wiersze, '£' i '*' po jednym, a '_'
    (########) zniknąłby cały. Dlatego wiersz glifu rozpoznajemy po KSZTAŁCIE
    (dokładnie SZER znaków ze zbioru '.#'), nie po pierwszym znaku.
    """
    glify, naglowek, wiersze = {}, None, []

    def domknij():
        nonlocal naglowek, wiersze
        if naglowek is not None:
            if len(wiersze) != WYS:
                raise ValueError(
                    f"{os.path.basename(sciezka)}: U+{naglowek[0]:04X} "
                    f"({naglowek[1]}) ma {len(wiersze)} wierszy, oczekiwano {WYS}")
            glify[naglowek[0]] = (naglowek[1], wiersze)
        naglowek, wiersze = None, []

    for lin in open(sciezka, encoding="utf-8"):
        lin = lin.rstrip("\n")
        if WIERSZ_GLIFU.match(lin):
            wiersze.append(lin)
            continue
        m = NAGLOWEK.match(lin)
        if m:
            domknij()
            naglowek = (int(m.group(1), 16), m.group(2).strip())
    domknij()
    return glify

# ── operacje na siatce ────────────────────────────────────────────────────────
def pusty():
    return ["." * SZER for _ in range(WYS)]

def naloz(spod, wierzch):
    """suma logiczna dwóch siatek"""
    out = []
    for a, b in zip(spod, wierzch):
        out.append("".join("#" if (x == "#" or y == "#") else "." for x, y in zip(a, b)))
    return out

def wzor(**kw):
    """wzor(w0='....##..', w8='...##...') -> siatka z podanymi wierszami"""
    g = pusty()
    for k, v in kw.items():
        g[int(k[1:])] = v[:SZER].ljust(SZER, ".")
    return g

def odbij(g):
    return [w[::-1] for w in g]

def przesun_w_dol(g, ile):
    return ["." * SZER] * ile + g[:-ile]

def zakres_kolumn(g):
    kol = [i for i in range(SZER) for w in g if w[i] == "#"]
    return (min(kol), max(kol)) if kol else (0, SZER - 1)

# ── AKCENTY (nasz projekt) ────────────────────────────────────────────────────
# nad WIELKĄ: jeden wiersz (indeks 0), płaski
OSTRY_DUZY  = wzor(w0="....##..")   # ´ 2px, przesunięty w prawo
KROPKA_DUZA = wzor(w0="...#....")   # ˙ 1px na środku — CIEŃSZA niż ostry
# 🔴 mina z dziennika 15.08: Ź i Ż różniące się tylko POZYCJĄ były nieodróżnialne.
#    Rozróżniamy GRUBOŚCIĄ: ostry = 2px w prawo, kropka = 1px na środku.

# nad MAŁĄ: jeden wiersz (1), a wiersz 2 zostaje PUSTY jako odstęp.
# Małe litery x-height zaczynają się w wierszu 3, więc akcent w wierszu 2
# przylegałby do nich bez przerwy i zlewał się w bryłę — dokładnie ten sam
# błąd, co nad wielkimi. Rezygnuję z ukosu dwuwierszowego na rzecz spójności
# z wielkimi literami i czytelnej przerwy.
OSTRY_MALY  = wzor(w1="....##..")
KROPKA_MALA = wzor(w1="...#....")

# ogonek — dwa wiersze pod linią bazową (8..9)
def ogonek(kol):
    """ogonek zaczepiony pod kolumną `kol`"""
    g = pusty()
    g[8] = "".join("#" if i in (kol, kol + 1) else "." for i in range(SZER))
    g[9] = "".join("#" if i in (kol - 1, kol) else "." for i in range(SZER))
    return g

def trzon(g):
    """kolumny tworzące pionowy trzon litery = te o największej liczbie wystąpień.
    L -> [1,2], l -> [3,4]. Dzięki temu kreska Ł/ł trafia w literę, a nie obok."""
    licznik = {}
    for w in g:
        for j in range(SZER):
            if w[j] == "#":
                licznik[j] = licznik.get(j, 0) + 1
    if not licznik:
        return [SZER // 2 - 1, SZER // 2]
    maks = max(licznik.values())
    return sorted(j for j, n in licznik.items() if n == maks)

def kreska_L(g):
    """ukośne przekreślenie trzonu w Ł/ł — wyliczane z POZYCJI trzonu w glifie.
    Ukos biegnie z dolnego-lewa do górnego-prawa (kierunek jak w polskiej typografii):
    górny wiersz kreski przesunięty o 1 px w PRAWO, dolny o 1 px w LEWO."""
    t = trzon(g)
    wiersze_trzonu = [i for i, w in enumerate(g) if all(w[j] == "#" for j in t)]
    if len(wiersze_trzonu) < 2:
        wiersze_trzonu = [4, 5]
    srodek = wiersze_trzonu[len(wiersze_trzonu) // 2]
    gora, dol = srodek - 1, srodek
    el = pusty()
    def linia(kolumny):
        return "".join("#" if j in kolumny else "." for j in range(SZER))
    el[gora] = linia({min(t) + 1, max(t) + 1})
    el[dol]  = linia({max(min(t) - 1, 0), min(t)})
    return el

def main():
    baza = czytaj(os.path.join(KAT, "src", "glify-baza.txt"))
    print(f"baza: {len(baza)} glifów")

    # ══ 1. brakujące ASCII ════════════════════════════════════════════════════
    dod = {}
    # \ = lustrzane odbicie /
    if 0x2F in baza:
        dod[0x5C] = ("REVERSE SOLIDUS", odbij(baza[0x2F][1]))
    dod[0x5E] = ("CIRCUMFLEX ACCENT", wzor(w1="...##...", w2="..####..", w3=".##..##."))
    dod[0x5F] = ("LOW LINE",          wzor(w8="########"))
    dod[0x60] = ("GRAVE ACCENT",      wzor(w1="..##....", w2="...##..."))
    dod[0x7B] = ("LEFT CURLY BRACKET",
                 wzor(w1="...###..", w2="..##....", w3="..##....", w4=".##.....",
                      w5="..##....", w6="..##....", w7="...###.."))
    dod[0x7C] = ("VERTICAL LINE",
                 wzor(w1="...##...", w2="...##...", w3="...##...", w4="...##...",
                      w5="...##...", w6="...##...", w7="...##..."))
    dod[0x7D] = ("RIGHT CURLY BRACKET", odbij(dod[0x7B][1]))
    # 🔴 Tylda przy 2 px kresce MUSI byc CIAGLA. Cztery odrzucone warianty (ukosna,
    # garb+dolina, symetryczna, obecna) czytaly sie jako dwie oddzielne plamki, bo
    # segmenty sie nie stykaly. Ten dziala, bo kolumna 3 nalezy do OBU wierszy.
    dod[0x7E] = ("TILDE", wzor(w4=".###....", w5="...####."))

    # ══ 2. polska interpunkcja ════════════════════════════════════════════════
    # „ ” ‚ ’ z cudzysłowów bazowych, – — z łącznika, … z kropek
    if 0x22 in baza:
        cud = baza[0x22][1]
        gora = [w for w in cud if "#" in w]
        dod[0x201D] = ("RIGHT DOUBLE QUOTATION MARK", wzor(w1=".##.##..", w2=".#..#..."))
        dod[0x201E] = ("DOUBLE LOW-9 QUOTATION MARK", wzor(w7=".##.##..", w8="..#..#.."))
    dod[0x2019] = ("RIGHT SINGLE QUOTATION MARK", wzor(w1="...##...", w2="...#...."))
    dod[0x201A] = ("SINGLE LOW-9 QUOTATION MARK",  wzor(w7="...##...", w8="..#....."))
    dod[0x2013] = ("EN DASH",  wzor(w5="..####.."))
    dod[0x2014] = ("EM DASH",  wzor(w5=".######."))
    dod[0x2026] = ("HORIZONTAL ELLIPSIS", wzor(w7="#..#..#."))
    dod[0x00A0] = ("NO-BREAK SPACE", pusty())

    # ══ 3. polskie diakryty ═══════════════════════════════════════════════════
    # (kod, baza, element, opis)
    przepisy = [
        (0x0104, 0x41, "ogonek_duzy",  "LATIN CAPITAL LETTER A WITH OGONEK"),
        (0x0106, 0x43, OSTRY_DUZY,     "LATIN CAPITAL LETTER C WITH ACUTE"),
        (0x0118, 0x45, "ogonek_duzy",  "LATIN CAPITAL LETTER E WITH OGONEK"),
        (0x0141, 0x4C, "kreska_L",     "LATIN CAPITAL LETTER L WITH STROKE"),
        (0x0143, 0x4E, OSTRY_DUZY,     "LATIN CAPITAL LETTER N WITH ACUTE"),
        (0x00D3, 0x4F, OSTRY_DUZY,     "LATIN CAPITAL LETTER O WITH ACUTE"),
        (0x015A, 0x53, OSTRY_DUZY,     "LATIN CAPITAL LETTER S WITH ACUTE"),
        (0x0179, 0x5A, OSTRY_DUZY,     "LATIN CAPITAL LETTER Z WITH ACUTE"),
        (0x017B, 0x5A, KROPKA_DUZA,    "LATIN CAPITAL LETTER Z WITH DOT ABOVE"),
        (0x0105, 0x61, "ogonek_maly",  "LATIN SMALL LETTER A WITH OGONEK"),
        (0x0107, 0x63, OSTRY_MALY,     "LATIN SMALL LETTER C WITH ACUTE"),
        (0x0119, 0x65, "ogonek_maly",  "LATIN SMALL LETTER E WITH OGONEK"),
        (0x0142, 0x6C, "kreska_l",     "LATIN SMALL LETTER L WITH STROKE"),
        (0x0144, 0x6E, OSTRY_MALY,     "LATIN SMALL LETTER N WITH ACUTE"),
        (0x00F3, 0x6F, OSTRY_MALY,     "LATIN SMALL LETTER O WITH ACUTE"),
        (0x015B, 0x73, OSTRY_MALY,     "LATIN SMALL LETTER S WITH ACUTE"),
        (0x017A, 0x7A, OSTRY_MALY,     "LATIN SMALL LETTER Z WITH ACUTE"),
        (0x017C, 0x7A, KROPKA_MALA,    "LATIN SMALL LETTER Z WITH DOT ABOVE"),
    ]

    pl = {}
    for kod, kod_bazy, elem, nazwa in przepisy:
        if kod_bazy not in baza:
            print(f"  !! brak bazy U+{kod_bazy:04X} dla U+{kod:04X}")
            continue
        g = baza[kod_bazy][1]
        if elem == "ogonek_duzy":
            l, p = zakres_kolumn(g)
            el = ogonek(p - 1 if kod == 0x0104 else 3)   # Ą: pod prawą nogą, Ę: środek
        elif elem == "ogonek_maly":
            l, p = zakres_kolumn(g)
            el = ogonek(p - 1 if kod == 0x0105 else 3)
        elif elem in ("kreska_L", "kreska_l"):
            el = kreska_L(g)
        else:
            el = elem
        pl[kod] = (nazwa, naloz(g, el))

    # ══ zapis ═════════════════════════════════════════════════════════════════
    def zapisz(sciezka, glify, tytul):
        out = [f"# ogonek64 — {tytul}", "# siatka 8 x 10, '.' zgaszony '#' zapalony",
               "# wiersze: 0=akcent nad wielką · 1..7=korpus · 8..9=pod linią bazową", ""]
        for kod in sorted(glify):
            nazwa, g = glify[kod]
            out.append(f"U+{kod:04X} {nazwa}")
            out.extend(g)
            out.append("")
        open(sciezka, "w", encoding="utf-8").write("\n".join(out) + "\n")
        print(f"zapisano {os.path.relpath(sciezka, KAT)} — {len(glify)} glifów")

    zapisz(os.path.join(KAT, "src", "glify-dodatki.txt"), dod,
           "znaki, których C64 nie ma (ASCII + polska interpunkcja)")
    zapisz(os.path.join(KAT, "src", "glify-pl.txt"), pl,
           "polskie diakryty (baza C64 + nasze akcenty)")

    # ══ render kontrolny ══════════════════════════════════════════════════════
    print("\n" + "=" * 72)
    print("RENDER KONTROLNY — polskie diakryty")
    print("=" * 72)
    kolejnosc = [0x0104, 0x0106, 0x0118, 0x0141, 0x0143, 0x00D3, 0x015A, 0x0179, 0x017B,
                 0x0105, 0x0107, 0x0119, 0x0142, 0x0144, 0x00F3, 0x015B, 0x017A, 0x017C]
    for i in range(0, len(kolejnosc), 6):
        grupa = kolejnosc[i:i+6]
        print()
        print("   " + "      ".join(f"{chr(k)}       " for k in grupa))
        for w in range(WYS):
            lin = "   "
            for k in grupa:
                lin += pl[k][1][w] + "     "
            print(lin)
        print("   " + "      ".join(f"U+{k:04X}  " for k in grupa))

if __name__ == "__main__":
    main()
