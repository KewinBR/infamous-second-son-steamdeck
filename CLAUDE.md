# inFAMOUS Second Son - Steamdeck Version

Repositório público (quando o Kewin liberar) do port nativo do inFAMOUS Second Son para Steam Deck: instalador,
iniciador com atualização automática, README em português e inglês, créditos e aprendizados. O código do port
(GPL-2.0) fica no ramo `steam-deck-v2-up` do iss_pc na VPS, espelhado em `KewinBR/iss_pc-steamdeck` (ramo
`steam-deck`, privado até o lançamento); o trabalho de pesquisa e o diário ficam no repo privado
`steam-deck` (`projetos/infamous/`).

## Regras

1. **Nada do jogo entra aqui.** Nem pkg, eboot, param.sfo, áudio, vídeo, textura, fonte ou texto do jogo, nem a
   tradução PT-BR (privada). O `.gitignore` bloqueia os formatos conhecidos; conferir antes de cada commit.
2. **Logo:** em todo lugar onde o logo aparece (instalador, tela de abertura do port, artes da Steam, README, página
   do projeto) vai o logo **inFAMOUS SECOND SON + STEAMDECK VERSION** (`arte/logo-vertical.png`) ou a versão
   horizontal (`arte/logo-horizontal.png`, SECOND SON numa linha, para espaços pequenos e banners). Nunca o logo
   original sozinho. Decidido pelo Kewin em 2026-10-23.
3. **Estética:** tudo que a pessoa vê segue o jogo e o menu do port: amarelo `#F2B71E`, fundo escuro, estêncil
   (`ISS Deck Stencil`, instância fixa da Big Shoulders Stencil, OFL) e Barlow (OFL), artes do Delsin com o Deck e do
   Deck em neon (geradas no Google Flow, coleção "inFAMOUS Steam Deck" do projeto Kewin). Mudança visual: mostrar
   print ao Kewin antes.
4. **Créditos:** Kewin Lima (port para Steam Deck) aparece no instalador (primeira e última tela) e no README, junto
   dos projetos em que nos baseamos (seção Créditos do README).
5. **Dois idiomas:** todo texto da pessoa usuária existe em português (Brasil) e inglês (`instalador/textos.py`,
   `README.md` e `README.pt-BR.md`). Sem travessão e sem emoji.
6. **Publicar:** o repositório nasce privado. O Kewin vê o link privado e só ele libera o público.
7. **Releases:** tag SemVer `vX.Y.Z` + entrada no `CHANGELOG.md` + pacote `infamous-ss-deck-vX.Y.Z.tar.gz` (port +
   instalador + pkgx) anexado à release. O iniciador busca a última release antes de abrir o jogo.
8. **Opção do port = menu do botão View** (decidido pelo Kewin em 2026-10-24, depois que a aba Extras foi parar só
   no menu avançado). O port tem dois menus em `port/gpu/shim/tlg_overlay.cpp`: o do botão View, no estilo do jogo
   (`Build()`, abas Gráficos, Controle, Extras e Sobre), que é o que a pessoa usa; e o avançado, de desenvolvimento
   (`ExtrasTab()` e vizinhas, aberto por "Menu avançado"). Toda opção nova que a pessoa deve ver entra no menu do
   View (e também no avançado, se fizer sentido). Opção que pede salvar entra em `Snapshot`/`Changed()`, senão o
   menu fecha sem gravar. Antes de dizer que está pronto: abrir o menu do View no Deck (sessão de teste) e mostrar
   print da opção no lugar. Como, sem ninguém no controle: `TLG_PAD_FILE` com a palavra `view` aperta o View,
   `TLG_MENU_TAB=n` abre o menu na aba n (0 Gráficos, 1 Controle, 2 Extras, 3 Sobre) e
   `TLG_SHOT_OVERLAY=1 TLG_SHOT_EVERY_S=1` grava prints com o menu por cima (`*_hud_*.png` em `user/gpu-2`). O
   `xdotool` não chega na janela dentro do gamescope e a captura do X sai preta.

## Easter eggs (grafites do minigame de spray)

Pedido do Kewin em 2026-10-23: trocas bem-humoradas nos grafites do minigame (as respostas dele estão na página
local `G:\Meu Drive\CLIENTES\_Dev\Steamdeck\infamous\grafites-easter-egg\grafites.html`).

1. **Cor de destaque:** grafite de karma mau usa detalhes em destaque **vermelhos**; de karma bom, **azuis**. O do
   Reggie (sem karma) segue o original.
2. **Mesmo estilo e mesma posição:** estêncil e spray como o original, nada muda de lugar (as camadas de tinta e os
   moldes do minigame têm que bater com a arte final). Só a parte trocada é refeita; o resto fica idêntico.
3. **Temas** quando a ideia precisar de troca: crítica à exclusividade nos games, o reinado das IAs e memes
   brasileiros.
4. **Opcional no menu do port:** Extras > "Easter Eggs", liga e desliga.
5. **Surpresa:** o README cita a opção, mas **nunca mostra as imagens modificadas** nem lista o que muda.
6. **Nada do jogo no repo** (regra 1): `deck/easter-eggs/<hash>.tlgpatch` leva só os blocos BC3 redesenhados
   (`ferramentas/tlgpatch.py`); o port desfaz o tiling da textura do próprio jogo e troca esses blocos na hora de
   subir para a GPU (`TLG_TEXTURE_EASTER_DIR`, só com a opção ligada). Nome do arquivo = hash, para não entregar
   a surpresa. Kewin aprovou a primeira arte (Reggie) em 2026-10-23.

## Estrutura

| Pasta | O quê |
|---|---|
| `instalador/` | instalador Tk (`instalador.py`, `nucleo.py`, `textos.py`, `steam.py`), `assets/` gerados, `fontes/` OFL |
| `arte/` | logos e artes fonte |
| `ferramentas/` | `gerar_assets.py` (assets do instalador a partir de `arte/`), build do pkgx |
| `docs/` | aprendizados e notas técnicas públicas |

## Prévias

`DEMO=1 PRINTS=<pasta> python instalador/instalador.py` passa por todas as telas e salva um print de cada (no PC,
com Pillow; `IDIOMA=en` para inglês).
