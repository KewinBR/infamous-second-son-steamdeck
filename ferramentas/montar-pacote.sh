#!/usr/bin/env bash
# Monta o pacote da release: dist/infamous-ss-deck-vX.Y.Z.tar.gz com o port compilado (build do ramo steam-deck-v2
# na VPS), o pkgx estatico e os arquivos deste repo. Nada do jogo entra (o tarball do port so tem executaveis,
# bibliotecas e ferramentas; os arquivos do eboot sao gerados no Deck de quem joga).
#   bash ferramentas/montar-pacote.sh v1.0.0
set -euo pipefail
versao=${1:?versao, ex.: v1.0.0}
raiz=$(cd -- "$(dirname -- "$0")/.." && pwd)
vps=${VPS:-kewinlima@100.72.99.124}
dist=$raiz/dist
pkg=$dist/infamous-ss-deck
rm -rf "$pkg"; mkdir -p "$pkg/bin"
scp -q "$vps:steamdeck/iss_pc-pr402-deck/port/dist/infamous-linux-x86_64.tar.gz" "$pkg/port.tar.gz"
scp -q "$vps:steamdeck/pkgx-src/pkgx/pkgx-static" "$pkg/bin/pkgx"
cp -r "$raiz/instalador" "$raiz/deck" "$raiz/arte" "$pkg/"
cp "$raiz/rodar.sh" "$raiz/iniciar.sh" "$raiz/iniciador.py" "$raiz/instalar.sh" "$raiz/LICENSE" "$pkg/"
rm -rf "$pkg/instalador/__pycache__"
echo "$versao" > "$pkg/VERSAO"
chmod +x "$pkg/bin/pkgx" "$pkg/rodar.sh" "$pkg/iniciar.sh" "$pkg/instalar.sh"
# conferencia: nenhum arquivo do jogo
if tar tzf "$pkg/port.tar.gz" | grep -qiE '\.(pkg|psarc|bsf|sfo)$|eboot\.(bin|elf)$|/content\.bin$'; then
    echo "ERRO: arquivo do jogo no tarball do port"; exit 1
fi
# tar pelo Python: no Windows o tar perde o bit de execucao; aqui os executaveis saem 755 e o resto 644.
python - "$dist" "$versao" <<'PY'
import os, sys, tarfile
dist, versao = sys.argv[1], sys.argv[2]
exe = {"bin/pkgx", "rodar.sh", "iniciar.sh", "instalar.sh"}
def ajusta(ti):
    rel = ti.name.split("/", 1)[1] if "/" in ti.name else ""
    ti.mode = 0o755 if ti.isdir() or rel in exe else 0o644
    ti.uid = ti.gid = 0; ti.uname = ti.gname = ""
    return ti
with tarfile.open(os.path.join(dist, f"infamous-ss-deck-{versao}.tar.gz"), "w:gz") as t:
    t.add(os.path.join(dist, "infamous-ss-deck"), "infamous-ss-deck", filter=ajusta)
PY
ls -la "$dist/infamous-ss-deck-$versao.tar.gz"
