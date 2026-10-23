#!/usr/bin/env bash
# Instalador do inFAMOUS Second Son - Steamdeck Version, para o Modo Desktop do Steam Deck.
# Baixa a ultima release (port + instalador, uns 100 MB; nada do jogo) e abre o instalador.
# Pelo Konsole:  curl -L https://github.com/KewinBR/infamous-second-son-steamdeck/releases/latest/download/instalar.sh | bash
set -euo pipefail
repo=KewinBR/infamous-second-son-steamdeck
dest=$HOME/.local/share/infamous-ss-deck-instalador
mkdir -p "$dest"
url=$(curl -fsSL "https://api.github.com/repos/$repo/releases/latest" |
      python3 -c "import json,sys; r=json.load(sys.stdin); print(next(a['browser_download_url'] for a in r['assets'] if a['name'].startswith('infamous-ss-deck-') and a['name'].endswith('.tar.gz')))")
echo "Baixando $url"
curl -fL --progress-bar -o "$dest/pacote.tar.gz" "$url"
rm -rf "$dest/infamous-ss-deck"
tar -xzf "$dest/pacote.tar.gz" -C "$dest"
rm -f "$dest/pacote.tar.gz"
exec python3 "$dest/infamous-ss-deck/instalador/instalador.py"
