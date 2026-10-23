#!/usr/bin/env bash
# inFAMOUS Second Son - Steamdeck Version: abre o jogo pelo port nativo (chamado pelo iniciador.py, que antes busca
# atualizacoes). Caminhos no ~/.config/infamous-ss-deck/config.json (gravado pelo instalador): "port" (o pacote do
# port) e "jogo" (o jogo extraido, 1.07). Saves, cache de shaders e opcoes ficam em ~/.local/share/infamous-ss-deck/
# user: atualizar o port nunca mexe neles.
# Log desta abertura: ~/.local/share/infamous-ss-deck/logs/ (o ultimo em ultimo.log).
set -euo pipefail
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
export DBUS_SESSION_BUS_ADDRESS=${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}
app=$(cd -- "$(dirname -- "$(readlink -f "$0")")" && pwd)
cfg=$HOME/.config/infamous-ss-deck/config.json
ler() { python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get(sys.argv[2],''))" "$cfg" "$1"; }
iss=$(ler port)
jogo=$(ler jogo)
udir=$app/user

# Uma abertura por vez (duas juntas esgotam a memoria do Deck).
if pgrep -f "^$iss/out/tlg-probe" >/dev/null || [[ -n $(find /tmp/iss-ss-abrindo -newermt '-60 seconds' 2>/dev/null) ]]; then
    echo "o jogo ja esta abrindo ou aberto" >&2
    exit 0
fi
touch /tmp/iss-ss-abrindo
mkdir -p "$app/logs" "$udir"
log=$app/logs/iss-$(date +%Y%m%d-%H%M%S).log
exec > "$log" 2>&1
ln -sf "$log" "$app/logs/ultimo.log"
ls -t "$app/logs"/iss-*.log 2>/dev/null | tail -n +11 | xargs -r rm -f   # guarda as 10 ultimas
echo "inicio $(date '+%F %T')  versao $(ler versao)  port $iss  jogo $jogo"
unset LD_PRELOAD LD_LIBRARY_PATH
[[ -x "$iss/inFAMOUS Second Son" ]] || { echo "port nao encontrado em $iss"; exit 1; }
[[ -f $jogo/eboot.bin ]] || { echo "jogo nao encontrado em $jogo"; exit 1; }

# Pasta do jogo e idioma no settings.json do launcher do port.
python3 - "$jogo" <<'EOF'
import json, os, sys
f = os.path.expanduser('~/.config/infamous-launcher/settings.json')
os.makedirs(os.path.dirname(f), exist_ok=True)
d = json.load(open(f)) if os.path.exists(f) else {}
d['game_dir'] = sys.argv[1]
json.dump(d, open(f, 'w'), indent=2)
EOF
export ISS_USER_DIR=$udir
# Renderer v2 com os passes nativos (o que medimos e usamos no Deck).
if [[ ! -f $udir/tlg.ini ]]; then
    printf 'renderer=2\nnative_passes=1\n' > "$udir/tlg.ini"
fi

# Qualidade: aba Graficos do menu do port (gfx_* e particles no tlg.ini) vira os patches do jogo (gerar.py).
pasta=$udir/patches/steam-deck
mkdir -p "$pasta" "$udir/mods"
GERAR_EXTRA=$(python3 - "$udir/tlg.ini" <<'PYEOF'
import json, os, re, sys
txt = open(sys.argv[1]).read() if os.path.exists(sys.argv[1]) else ""
v = dict(re.findall(r"^(\w+)=(\S*)", txt, re.M))
g = lambda k, d: int(v.get(k, d))
e = {"resolucao": [1200, 1000, 800, 600, 800][min(4, g("gfx_resolution", 2))],  # 16:10
     "fov": [100, 95, 90, 85, 80][min(4, g("gfx_fov", 0))],
     "legenda_tamanho": [36, 42, 48, 54][min(3, g("gfx_subtitles", 2))],
     "ligacao_controle": True,
     "distancia": [100, 85, 70][min(2, g("gfx_distance", 2))],
     "motion_blur": bool(g("gfx_motion_blur", 0)), "reflexos": bool(g("gfx_ssr", 0)),
     "destravar_fps": bool(g("gfx_unlock_fps", 1))}
sh = min(2, g("gfx_shadows", 1))
e["sombras_reduzidas"] = sh > 0
if sh == 1: e.update(sombra_cascatas=3, sombra_distancia=10000)
if sh == 2: e.update(sombra_cascatas=2, sombra_distancia=6000)
pa = min(2, g("particles", 0))
if pa == 1: e.update(particulas_orcamento=256, particulas=0.75)
if pa == 2: e.update(particulas_orcamento=64, particulas=0.5)
print(json.dumps(e))
PYEOF
)
export GERAR_EXTRA
echo "qualidade: $GERAR_EXTRA"
if grep -qE '"resolucao": (1200|1000|800|600)[,}]' <<< "$GERAR_EXTRA"; then export TLG_VIDEO_CROP_1610=1; fi
python3 "$app/deck/gerar.py" "$pasta"
cp -f "$pasta/inFAMOUS.xml" "$udir/mods/steamdeck-inFAMOUS.xml"

# Controle: no Modo de Jogo a Steam entrega um controle virtual (sem giroscopio nem botoes de tras); o jogo le o
# do Deck direto.
controle=(env -u SDL_GAMECONTROLLER_ALLOW_STEAM_VIRTUAL_GAMEPAD SDL_GAMECONTROLLER_IGNORE_DEVICES=0x28DE/0x11FF)
# Giroscopio do Deck (a Steam deixa desligado): liga depois que o port abriu o controle e repete.
rm -f "$iss/out/last_run.log"
setsid python3 "$app/deck/ligar-imu.py" --manter "$iss/out/last_run.log" --marca "Runtime: gamepad connected" \
    --processo "[o]ut/tlg-probe" --atual "$iss/out/last_run.log" --espera 1800 </dev/null >/dev/null 2>&1 &
# Botao Steam e menu rapido congelam o jogo, como o botao PS.
export TLG_STEAM_PAUSE_FILE=/tmp/iss-ss-pausa-steam
rm -f "$TLG_STEAM_PAUSE_FILE"
if [[ -n ${SteamAppId:-} ]]; then
    setsid python3 "$app/deck/congelar-no-menu-steam.py" "$SteamAppId" "[o]ut/tlg-probe" "$TLG_STEAM_PAUSE_FILE" \
        </dev/null >>"$app/logs/congelar.log" 2>&1 &
fi

# Padroes medidos no Deck (ver docs/aprendizados): tcmalloc do SteamOS, vblank livre, threads criticas fora do
# nucleo fisico 0 (mais lento), pipeline de desenho de 3 threads desligado, letras A/B do Deck.
[[ -f /usr/lib/libtcmalloc_minimal.so.4 ]] && controle+=(LD_PRELOAD=/usr/lib/libtcmalloc_minimal.so.4)
export TLG_VBLANK_HZ=0 TLG_DRAW_PIPE=0 TLG_GLYPHS=xbox TLG_SUBMIT_DRAWS=256 TLG_REPEAT_BIND=1
case ${LANG:-}${LC_ALL:-} in pt*) export TLG_UI_LANG=pt_BR ;; *) export TLG_UI_LANG=en_US ;; esac
# Menu do port e tela de abertura: fontes livres (OFL) e o logo Steamdeck Version.
export TLG_MENU_FONT=$app/instalador/fontes/Barlow-Medium.ttf TLG_MENU_FONT_BOLD=$app/instalador/fontes/ISSDeckStencil.ttf
export TLG_LOADING_ART=$app/arte/delsin-steamdeck.png TLG_LOADING_LOGO=$app/arte/logo-vertical.png
# Texturas trocadas pelo port: o Deck no lugar do controle do PS4 (minigame do spray e tela de controles).
export TLG_TEXTURE_REPLACE_DIR=$app/deck/texturas
export TLG_RESTART_COMMAND="bash $app/rodar.sh"
setsid python3 "$app/deck/fixar-threads.py" "tlg:DrawRec=6;shadPS4:GpuComm=4;*=0-3,5,7" \
    </dev/null >"$app/logs/fixar-threads.log" 2>&1 &

rm -f /tmp/iss-ss-abrindo
cd "$iss"
exec "${controle[@]}" "./inFAMOUS Second Son" --play
