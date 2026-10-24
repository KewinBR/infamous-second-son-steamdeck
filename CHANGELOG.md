# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), versões em [SemVer](https://semver.org/lang/pt-BR/).

## [1.0.4] - 2026-10-24

### Corrigido
- O botão Steam ainda podia travar o Deck em sessões longas. A causa de verdade: os passes nativos do renderer
  guardavam os buffers de comando de cada pico de cena pesada e nunca devolviam (chegava a ~3 GB de memória de vídeo).
  Agora o que sobra acima do necessário volta pro sistema.

## [1.0.3] - 2026-10-24

### Corrigido
- A proteção de memória da 1.0.2 apagava texturas em uso e o jogo engasgava nas batalhas. Agora ela só apaga texturas
  paradas há uns 20 segundos, poucas de cada vez.

## [1.0.2] - 2026-10-24

### Corrigido
- O botão Steam podia travar o Deck depois de um bom tempo de jogo: a memória de vídeo (que no Deck sai da RAM)
  enchia e o menu da Steam não conseguia abrir. Agora o port libera texturas fora de uso quando a memória livre do
  Deck cai abaixo de 1,5 GB.

## [1.0.1] - 2026-10-24

### Corrigido
- A aba Extras (Pular vídeos e Easter Eggs) agora aparece no menu do botão View; antes estava só no menu avançado.

## [1.0.0] - 2026-10-23

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
