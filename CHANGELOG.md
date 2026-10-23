# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), versões em [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Adicionado
- Instalador para o Modo Desktop do Steam Deck (toque e controle, português e inglês): acha os .pkg do jogo,
  extrai com o pkgx, instala o port e cria o atalho na Steam.
- Logo inFAMOUS SECOND SON + STEAMDECK VERSION (vertical e horizontal) e artes do instalador.
- Icones de botao do Deck no jogo (A, B, X, Y, MENU, PAD), gerados no Deck a partir dos pacotes de texto do jogo, em
  Python puro (15 idiomas em ~20 s).
- Texturas do Deck: minigame do spray (chacoalhar, virar) e tela de controles com os botoes de tras.
- Atalho na Steam com capa, banner, fundo, logo e icone; iniciador com atualizacao automatica.
- Extras > Easter Eggs no menu do port (desligado por padrao). Os arquivos levam so os blocos de textura
  redesenhados; o resto vem do jogo instalado (`ferramentas/tlgpatch.py`).
