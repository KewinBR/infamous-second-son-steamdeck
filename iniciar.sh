#!/usr/bin/env bash
# Atalho da Steam: verifica atualizacao e abre o jogo (iniciador.py -> rodar.sh).
app=$(cd -- "$(dirname -- "$(readlink -f "$0")")" && pwd)
exec python3 "$app/iniciador.py" "$@"
