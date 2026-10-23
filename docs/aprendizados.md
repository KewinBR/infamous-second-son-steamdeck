# Aprendizados: levando o inFAMOUS Second Son para o Steam Deck

Diário técnico, do mais antigo ao mais novo, do que funcionou, do que não funcionou e por quê. Os números são do
Steam Deck LCD (SteamOS 3.8), medidos com trajetos gravados: o controle de uma sessão de jogo é gravado e reproduzido
igual, então dá para comparar configurações na mesma cena. Duas rodadas iguais variam de 1 a 3 FPS; ganho pequeno
só conta com várias rodadas.

## 1. Do emulador ao port nativo

- O primeiro caminho foi o shadPS4 rodando no Deck: funcionava, mas pesado nas cenas de ação.
- O [iss_pc](https://github.com/HayatoG/iss_pc) recompila o executável do jogo para x86-64 e só emula o que é do
  PS4 (GPU, áudio, arquivos). Compilado para o Deck num container Arch (distrobox) e depois numa máquina Linux à
  parte, ele virou a base.

## 2. Memória (o que mais pesou)

- **Congelamento depois de 40 min de jogo:** falta de memória. O relatório de memória do renderer mostrou a arena de
  buffers com 3,2 GB (uma cópia dos heaps de GPU do jogo), as texturas com 1,2 a 1,5 GB e o jogo com 6 GB de RAM.
- **Heap unificado:** a GPU passa a ler os dois heaps do jogo no lugar (`ISS_UNIFIED_RANGE`), sem a cópia. O primeiro
  teste travou o Deck: o tamanho tinha 64 KB a mais que o heap e o renderer recusou o modo unificado em silêncio,
  ficando com a arena e o mapeamento juntos. Com o tamanho exato: arena 0, RAM do jogo 3,4 a 4 GB, corrida de neon de
  33 para 42 FPS de média.
- **Coletor de texturas:** ele comparava o uso total de memória do dispositivo com o orçamento. No Deck a memória é
  compartilhada, o total nunca caía e o coletor apagava texturas todo quadro (que o jogo recriava logo em seguida:
  travadas). Passando a medir só as texturas, as travadas sumiram.
- **Travamento da lista LRU:** um item liberado podia ser religado na lista e o coletor entrava em ciclo. A versão do
  port original corrigiu o mesmo problema de outro jeito; as duas correções estão juntas aqui.

## 3. Shaders

- O jogo tem 10.374 shaders (8.049 de cálculo, 1.986 de vértice, 339 de pixel). O renderer v2 compila os de cálculo
  antes de jogar; os gráficos dependem do estado de cada passe (alvos, formatos, profundidade).
- Combinar cada par de shaders com todos os estados já vistos dá 85 mil pipelines, seis vezes o cache real, quase
  tudo combinação que o jogo nunca desenha. Sem a lista de materiais do jogo (como os ports de PC que compilam tudo na
  abertura têm), a estratégia que funciona é o cache: cada pipeline novo é salvo e a abertura seguinte já carrega.
  Uma sessão de uma hora gerou 219 novos; a seguinte, nenhum na mesma região.
- Salvar o cache a cada 30 s travava a criação de pipelines por 0,5 a 3 s; a cada 5 min (e no carregamento e na
  saída) não se nota.

## 4. Onde vai o tempo de um quadro

- Na corrida de neon, o quadro médio tem 25 ms e a GPU trabalha 15,5 deles. O processador de comandos (que traduz os
  comandos de GPU do PS4) ocupa a maior parte do quadro e cresce com o número de desenhos (cerca de 7,5 µs cada).
- Pilhas de chamada da thread do jogo (o código recompilado mantém o ponteiro de quadro, então o `perf -g` funciona)
  mostraram 41% do tempo numa espera ativa: o laço principal espera um rótulo que a GPU escreve no fim do trabalho e
  só segue quando a fila inteira esvazia. CPU e GPU se revezam em vez de trabalhar juntas.
- Um patch de 18 bytes faz o jogo esperar só até um quadro atrás: de 40 para 45 FPS de média nas mesmas rodadas,
  mas o neon, a fumaça e as explosões somem (o jogo lê a simulação de partículas que a GPU calcula antes dela ficar
  pronta) e até o trajeto gravado muda de caminho. Uma segunda espera, na função que envia o quadro, trava o
  carregamento se for relaxada. Descartado: a espera existe por um motivo.

## 5. Vídeos

- **16:10:** o decodificador do port corta os vídeos 16:9 para 16:10 e eles enchem a tela, sem barras. Ainda sobra
  uma faixa de umas 45 linhas no topo, que vem de como o jogo posiciona o vídeo com a resolução 16:10 (em estudo).
- **Pular vídeo:** o arquivo do vídeo passa a ler fim de arquivo. O jogo já tinha lido uns 20 MB adiantados, então o
  áudio da cena continuava por uns 6,5 s: o áudio fica mudo até a cena voltar (pelo menos 8 s). O fim da cena é
  detectado pelo número de desenhos por quadro (um vídeo em tela cheia desenha de 1 a 9 coisas; o jogo, centenas).
  O aviso só aparece com o vídeo da cena em tela cheia e sendo lido; televisões e vídeos da interface não contam.

## 6. Controle e Steam

- A Steam desliga o giroscópio do controle do Deck quando o layout dela não usa giroscópio, e entrega um controle
  virtual ao jogo. O port lê o controle do Deck direto (ignorando o virtual) e um script liga o giroscópio pelo
  relatório de configuração do controle, sem senha.
- O botão Steam e o menu rápido congelam o jogo, como o botão PS: o foco do gamescope muda para a Steam e o port
  escurece e pausa as threads do jogo.
- A Steam reescreve o `shortcuts.vdf` enquanto está aberta: para criar o atalho, fecha a Steam, grava (mantendo os
  outros atalhos byte a byte) e deixa a sessão abrir de novo.

## 7. Processador do Deck

- O núcleo físico 0 (CPUs 0 e 1) roda a uns 2,4 GHz; os outros, a 3,48 GHz. As threads críticas do port ficam fora
  dele.
- O tcmalloc do SteamOS no lugar do alocador da glibc dá uns 4% (a glibc gastava 15% da thread de desenho percorrendo
  listas de blocos livres).
- O pipeline de desenho de 3 threads é mais lento no Deck (26 contra 30 FPS) e fica desligado.

## 8. Extração dos .pkg

- O PkgTool da LibOrbisPkg grava zeros em partes de alguns arquivos.
- O código de extração do shadPS4 0.6.0, num programa de linha de comando (`pkgx`), extrai certo. Correções: contas
  de tamanho em 64 bits (arquivos de 2 GB ou mais), estouro de buffer na decifragem de entradas com tamanho que não é
  múltiplo de 16 e avisos em vez de silêncio quando uma leitura volta curta.
- Compilado de forma estática, roda no SteamOS sem instalar nada.
