# inFAMOUS Second Son - Steamdeck Version

Repositório público (quando o Kewin liberar) do port nativo do inFAMOUS Second Son para Steam Deck: instalador,
iniciador com atualização automática, README em português e inglês, créditos e aprendizados. O código do port
(GPL-2.0) fica no ramo `steam-deck-v2` do fork do iss_pc; o trabalho de pesquisa e o diário ficam no repo privado
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
