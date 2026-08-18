#!/usr/bin/env bash
# ============================================================================
#  Ogonek 64 -> google/fonts : przygotowanie trzech PR-ow
#
#  Co robi:  fork google/fonts, plytki klon (repo ma 3 GB!), trzy galezie,
#            po jednej na rodzine, commit + push. PR-y tworzy na koncu.
#  Czego NIE robi: nie dotyka Twoich repozytoriow ogonek64 i c64-terminal-pl.
#
#  Wymaga: gh zalogowany, podpisany CLA TYM SAMYM adresem e-mail co commity.
# ============================================================================
set -euo pipefail

ZRODLO="$HOME/oskar/ogonek64/gf/ofl"
PRACA="${1:-$HOME/oskar/gf-pr}"
GALEZ_BAZOWA="main"

# rodzina : katalog : tytul PR
RODZINY=(
  "ogonek64mono:Ogonek 64 Mono"
  "ogonek64sans:Ogonek 64 Sans"
  "ogonek64crt:Ogonek 64 CRT"
)

echo "▶ 1/5  Sprawdzam tozsamosc"
MAIL=$(git config --global user.email)
echo "   commity beda podpisane: $MAIL"
echo "   🔴 To MUSI byc ten sam adres, ktorym podpisales CLA. Jesli nie — przerwij (Ctrl-C)."
read -r -p "   Zgadza sie? [T/n] " o; case "${o:-t}" in [TtYy]*) ;; *) echo "przerwane"; exit 1 ;; esac

echo "▶ 2/5  Fork google/fonts (jesli jeszcze nie masz)"
gh repo fork google/fonts --clone=false --remote=false 2>&1 | sed 's/^/   /' || true

echo "▶ 3/5  Klon plytki i rzadki (repo ma 3 GB, bierzemy tylko to, co trzeba)"
KONTO=$(gh api user -q .login)
if [ ! -d "$PRACA/.git" ]; then
    mkdir -p "$(dirname "$PRACA")"
    # --filter=blob:none  -> bloby sciagane na zadanie, nie wszystkie 3 GB
    # --sparse            -> w katalogu roboczym tylko wybrane sciezki
    git clone --filter=blob:none --sparse "https://github.com/$KONTO/fonts.git" "$PRACA"
    cd "$PRACA"
    git sparse-checkout set ofl/ogonek64mono ofl/ogonek64sans ofl/ogonek64crt
    git remote add upstream https://github.com/google/fonts.git
else
    cd "$PRACA"
    echo "   katalog juz istnieje — odswiezam z upstreamu"
fi

cd "$PRACA"
git fetch upstream "$GALEZ_BAZOWA" --quiet
git checkout -q -B "$GALEZ_BAZOWA" "upstream/$GALEZ_BAZOWA"

echo "▶ 4/5  Trzy galezie, po jednej na rodzine"
for wpis in "${RODZINY[@]}"; do
    KAT="${wpis%%:*}"; NAZWA="${wpis#*:}"
    git checkout -q -B "$KAT" "upstream/$GALEZ_BAZOWA"
    mkdir -p "ofl/$KAT"
    cp -r "$ZRODLO/$KAT/." "ofl/$KAT/"
    git add "ofl/$KAT"
    git commit -q -m "$NAZWA: Version 1.003 added

New pixel typeface with full GF Latin Core coverage (319 glyphs) and
complete Polish diacritics, built on an 8x12 grid.

Source: https://github.com/arekbr/ogonek64
Designer: SMOK - Arek Bronowicki
License: SIL OFL 1.1, no Reserved Font Name

fontbakery check-googlefonts: 0 FAIL"
    git push -q -f origin "$KAT"
    echo "   ✓ galaz $KAT wypchnieta"
done

echo "▶ 5/5  Tworze PR-y"
for wpis in "${RODZINY[@]}"; do
    KAT="${wpis%%:*}"; NAZWA="${wpis#*:}"
    gh pr create --repo google/fonts --base "$GALEZ_BAZOWA" --head "$KONTO:$KAT" \
      --title "$NAZWA: Version 1.003 added" \
      --label "I New Font" \
      --body "## $NAZWA

New pixel typeface on an 8x12 grid, covering the full **GF Latin Core** glyph set (319 glyphs) with complete Polish diacritics — which 8-bit character sets never had.

**Source repository:** https://github.com/arekbr/ogonek64
**Designer:** SMOK - Arek Bronowicki
**License:** SIL OFL 1.1, no Reserved Font Name
**CLA:** signed

### QA

\`fontbakery check-googlefonts\` — **0 FAIL** across 455 check executions.
Remaining WARNs are inherent to a pixel design (\`contour_count\`, \`unreachable_subsetting\`) or require a designer profile that comes with onboarding.

### Design notes

Accents occupy two dedicated rows plus one of clearance. In a single row of eight pixels the circumflex, caron, breve, ring and diaeresis are indistinguishable from one another, so the cell is twelve pixels tall rather than eight. Accent placement is computed from each letter's actual top edge, which keeps capitals, ascenders and x-height glyphs consistent; the accent over \`i\`/\`j\` replaces the dot.

Glyph sources are plain text files, one line per pixel row, so the build is reproducible and reviewable without a font editor." 2>&1 | sed 's/^/   /'
done

echo
echo "GOTOWE. Trzy PR-y otwarte, z etykieta \"I New Font\"."
echo "Status (II ...) ustawiaja opiekunowie — nie dodawaj sam."
echo "Review odbywa sie we wtorki i srody. Od PR do publikacji zwykle 3-6 tygodni."
