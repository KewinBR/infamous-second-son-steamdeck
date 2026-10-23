<p align="center"><img src="arte/logo-vertical.png" width="420" alt="inFAMOUS Second Son - Steamdeck Version"></p>

<p align="center"><b>Português</b> • <a href="README.md">English</a></p>

# inFAMOUS Second Son: Steamdeck Version

Port nativo do inFAMOUS Second Son (PS4) para o Steam Deck, sem emulador. Ele roda a partir do
[iss_pc](https://github.com/HayatoG/iss_pc) de HayatoG (recompilação do jogo para PC, com o renderer v2), com o
trabalho específico do Deck descrito abaixo: desempenho, memória, controle, telas e um instalador que dispensa
teclado e mouse.

**Você precisa da sua própria cópia do jogo.** Este repositório não tem nenhum arquivo do jogo e nada do jogo é
baixado: o instalador só usa os `.pkg` que você já tem.

<p align="center"><img src="docs/img/instalador-1-inicio-pt.jpg" width="640" alt="Instalador"></p>

## O que tem nesta versão

- Jogo jogável do começo ao fim: zerado no Deck com karma bom; o caminho do karma mau está sendo jogado agora.
- Renderer v2 com memória ajustada para os 16 GB do Deck: o jogo usa uns 3,5 GB de RAM em vez de 6, e o trecho mais
  pesado testado (a corrida de neon) foi de 33 para 41 FPS de média.
- Resolução 16:10 nativa da tela do Deck, com os vídeos cortados para 16:10.
- Giroscópio do Deck no minigame de grafite, botão Steam pausa o jogo (como o botão PS), menu do port no botão View.
- Telas de salvar e de carregamento no estilo do jogo, letras A/B do Deck.
- Cache de shaders: cada shader é compilado uma vez só e guardado.
- Pular vídeos (experimental, desligado de fábrica): no menu do port, aba Extras.
- Atualização automática: antes de abrir o jogo, o atalho confere se saiu versão nova e atualiza sozinho. Saves,
  shaders e opções nunca são apagados.

## Requisitos

- Steam Deck (testado no SteamOS 3.8).
- Os `.pkg` do seu jogo: o jogo base (24 GB) e a atualização 1.07 (3,9 GB).
  - **CUSA00004** (Europa): a versão testada no Deck, do começo ao fim.
  - **CUSA00223** (EUA): a versão principal do port original; o executável 1.07 é o mesmo.
- 32 GB livres no SSD ou no cartão microSD, além do espaço dos `.pkg`.
- Internet só para baixar o port (uns 110 MB).

## Instalação (sem teclado e sem mouse)

1. Copie os `.pkg` para o Deck: para a pasta **Downloads** ou para o **cartão microSD** (qualquer pasta). Pelo PC,
   dá para usar um pen drive, o cartão SD ou o Warpinator.
2. No Deck, segure o botão de ligar e escolha **Mudar para a Área de Trabalho** (Modo Desktop).
3. Abra o navegador, entre na página de [releases](https://github.com/KewinBR/infamous-second-son-steamdeck/releases/latest)
   e baixe o arquivo **`Instalar inFAMOUS.desktop`**.
4. Na pasta Downloads, toque duas vezes nele (se o sistema perguntar, escolha **Continuar/Executar**).
5. O instalador abre em tela cheia. Use o toque ou o controle (direcional, **A** confirma, **B** volta):
   1. **Onde está o jogo:** ele acha os `.pkg` sozinho e marca o jogo e a atualização.
   2. **Onde instalar:** SSD (carrega mais rápido) ou cartão microSD.
   3. **Instalando:** extrai o jogo e aplica a 1.07 (uns 20 minutos; deixe o Deck na tomada).
   4. **Pronto:** toque em **Voltar ao Modo de Jogo**. O jogo aparece na biblioteca da Steam com capa e ícone.

Prefere o Konsole? Uma linha faz o mesmo que os passos 3 e 4:

```bash
curl -L https://github.com/KewinBR/infamous-second-son-steamdeck/releases/latest/download/instalar.sh | bash
```

<p align="center">
<img src="docs/img/instalador-2-jogo-pt.jpg" width="420" alt="Onde está o jogo">
<img src="docs/img/instalador-4-instalando-pt.jpg" width="420" alt="Instalando">
</p>

### Já tenho o jogo extraído

Na tela "Onde está o jogo", escolha **Já tenho a pasta extraída** e aponte a pasta que tem o `eboot.bin` e a pasta
`sce_sys` (o jogo base com a atualização 1.07 copiada por cima).

### Extrair os .pkg na mão (opcional)

O instalador faz isso sozinho. Se quiser extrair por conta própria, o pacote da release traz o `pkgx` (o extrator do
shadPS4 0.6.0 em linha de comando, sem dependências):

```bash
./bin/pkgx "Infamous Second son.pkg" ~/jogos/inFAMOUS
```

```bash
./bin/pkgx "inFAMOUS Second Son-up.pkg" ~/jogos/inFAMOUS
```

O primeiro extrai o jogo base; o segundo aplica a atualização 1.07 por cima, na mesma pasta. Depois, use a opção
**Já tenho a pasta extraída** no instalador.

## Jogando

- **Primeira abertura:** a tela de carregamento prepara os shaders (alguns minutos, uma vez só).
- **Menu do port:** botão **View** (o de dois quadradinhos, à esquerda da tela). Gráficos, desempenho, controle e a
  aba Extras.
- **Botão Steam:** pausa o jogo enquanto o menu da Steam estiver aberto.
- **Pular vídeos:** ligue em Extras > Pular vídeos (Experimental); durante um vídeo, segure o botão de menu por 1 s.

## Atualizações

O atalho da Steam passa por um iniciador que, antes de abrir o jogo, confere a última release deste repositório. Se
tiver versão nova, mostra a tela "Atualizando", baixa só o port e abre o jogo em seguida. Sem internet, o jogo abre
na versão instalada. Para desligar, mude `"atualizar": false` em `~/.config/infamous-ss-deck/config.json`.

## Desinstalar

Apague a pasta `infamous-ss-deck` (no SSD fica na sua pasta pessoal; no cartão, na raiz dele), a pasta
`~/.local/share/infamous-ss-deck` (saves e shaders: guarde a `user/savedata` se quiser os saves) e o atalho na
Steam.

## Problemas

- O registro de cada abertura fica em `~/.local/share/infamous-ss-deck/logs/ultimo.log`.
- O do instalador, em `~/.config/infamous-ss-deck/instalador.log`.
- Abra uma [issue](https://github.com/KewinBR/infamous-second-son-steamdeck/issues) com o registro e o que
  aconteceu.

## Créditos

**Port para Steam Deck:** Kewin Lima.

Este trabalho existe por causa destes projetos (todos GPL-2.0, como este):

- [iss_pc](https://github.com/HayatoG/iss_pc), de HayatoG (Guilherme): o port nativo do inFAMOUS Second Son para PC,
  incluindo o renderer v2 ([PR #402](https://github.com/HayatoG/iss_pc/pull/402)). A base de tudo aqui.
- As bases do iss_pc: [tlg_pc](https://github.com/HayatoG/tlg_pc) e [gr2_pc](https://github.com/HayatoG/gr2_pc)
  (HayatoG), [gow3_pc](https://github.com/FelipePrado0/gow3_pc) (FelipePrado0),
  [bloodborne_pc](https://github.com/deadinside28/bloodborne_pc) (deadinside28),
  [shadPS4](https://github.com/shadps4-emu/shadPS4) e o fork
  [shadPS4-Infamous-FixBuild](https://github.com/rayhlancaner-png/shadPS4-Infamous-FixBuild) (Eye Of The Ruins,
  TOXIC-KID, 0xDeftones), [ShadowOfTheColossus-PC](https://github.com/AjncSystem/ShadowOfTheColossus-PC) (AjncSystem,
  com partes do Pink-shadPS4 de luizgustavs).
- O extrator de `.pkg` (`pkgx`) é o código de extração do [shadPS4](https://github.com/shadps4-emu/shadPS4) 0.6.0
  num programa de linha de comando, com correções para arquivos grandes.
- Fontes do instalador: Big Shoulders Stencil (The Big Shoulders Project Authors) e Barlow (Jeremy Tribby), licença
  SIL OFL 1.1.
- Artes do Delsin com o Steam Deck e do Deck em neon: geradas no Google Flow para este projeto.

inFAMOUS e inFAMOUS Second Son são marcas da Sony Interactive Entertainment; o jogo é da Sucker Punch Productions.
Este é um projeto de fãs, sem relação com elas.

## O que aprendemos no caminho

O diário completo fica em [docs/aprendizados.md](docs/aprendizados.md). Os principais pontos:

- **Memória:** o renderer copiava 3,2 GB da memória da GPU do jogo para uma arena própria. Apontando a GPU direto
  para os dois heaps do jogo (heap unificado, com o tamanho exato: 64 KB a mais e o renderer recusa), a RAM do jogo
  caiu de 6 para 3,5 GB e a corrida de neon foi de 33 para 41 FPS.
- **Coletor de texturas:** medindo o uso total do Deck (que inclui a memória compartilhada), ele apagava texturas
  todo quadro. Medindo só as texturas, as travadas sumiram.
- **Onde vai o quadro:** o jogo espera a GPU esvaziar a fila a cada quadro. Esperar um quadro a menos deu uns 4 FPS
  a mais, mas o neon, a fumaça e as explosões sumiram: o jogo lê a simulação de partículas que a GPU calcula, e ela
  ainda não estava pronta. Descartado.
- **Shaders:** o jogo tem 10.374 shaders e 13 mil combinações de pipeline já vistas. Compilar tudo de antemão não
  funciona sem a lista de materiais do jogo; o cache guarda cada pipeline compilado e a abertura seguinte já os
  carrega.
- **Extração:** o PkgTool da LibOrbisPkg grava zeros em partes de alguns arquivos; o código do shadPS4 extrai certo.
- **Steam Deck:** a Steam reescreve o `shortcuts.vdf` enquanto está aberta (o instalador fecha a Steam, grava e
  deixa ela voltar); a Steam desliga o giroscópio do controle e entrega um controle virtual (o port lê o controle
  do Deck direto e liga o giroscópio); o núcleo físico 0 do Deck roda mais devagar que os outros (as threads
  críticas ficam fora dele).

## Licença

GPL-2.0, como o iss_pc ([LICENSE](LICENSE)). O código do port, com todas as mudanças feitas para o Deck, está em
[KewinBR/iss_pc-steamdeck](https://github.com/KewinBR/iss_pc-steamdeck) (ramo `steam-deck`). As fontes do instalador seguem a SIL OFL 1.1
(`instalador/fontes/`).
