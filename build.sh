#!/usr/bin/env bash
# ogonek64 — pełna budowa czterech odmian JEDNYM poleceniem:
#
#   ./build.sh
#
# Wynik: fonts/ttf/*.ttf + fonts/webfonts/*.woff2
#
# Zależności: python3 (>=3.9) i pakiety z requirements.txt. Skrypt sam zakłada
# środowisko `.venv`, jeśli go nie ma — nie dotyka pakietów systemowych.
#
# Przełączniki:
#   --skip-tests   pominięcie kontroli (domyślnie kontrola JEST uruchamiana)
#   --no-venv      użyj `python3` z PATH zamiast zakładać `.venv`

set -euo pipefail
cd "$(dirname "$0")"   # 🔴 razem z `set -e`: nieudane wejście do katalogu przerywa skrypt,
                       #    zamiast puścić resztę poleceń w cudzym katalogu

TESTY=1
VENV=1
for arg in "$@"; do
  case "$arg" in
    --skip-tests) TESTY=0 ;;
    --no-venv)    VENV=0 ;;
    -h|--help)    sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "nieznany przełącznik: $arg" >&2; exit 2 ;;
  esac
done

if [ "$VENV" -eq 1 ]; then
  if [ ! -x .venv/bin/python ]; then
    echo "== zakładam środowisko .venv =="
    python3 -m venv .venv
    .venv/bin/pip install --quiet --upgrade pip
    .venv/bin/pip install --quiet -r requirements.txt
  fi
  PY=.venv/bin/python
else
  PY=python3
fi

echo "== glify pochodne (akcenty, ogonki, interpunkcja) =="
"$PY" sources/zrob_glify.py

echo "== uzupełnienie do GF Latin Core =="
"$PY" sources/glify_latin.py

echo "== budowa TTF =="
"$PY" sources/buduj.py

echo "== kompresja WOFF2 =="
"$PY" sources/webfonts.py

if [ "$TESTY" -eq 1 ]; then
  echo "== kontrola =="
  "$PY" tests/kontrola.py
fi

echo
echo "gotowe: fonts/ttf/*.ttf + fonts/webfonts/*.woff2"
