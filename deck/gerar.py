#!/usr/bin/env python3
"""Gera user/patches/steam-deck/inFAMOUS.xml a partir de opcoes.json (editado pelo painel do emulador).

Uso: gerar.py <pasta user/patches/steam-deck>
Opções (opcoes.json), com os padrões = configuração aprovada em 2026-10-15:
  resolucao: 16:10 1200 | 1000 | 800 | 600; 16:9 1080 | 900 | 720 | 540        (renderização e saída no mesmo tamanho, patch v3)
  distancia: 30..100                        (% da distância de desenho: escala global + faixas longas)
  sombras_reduzidas: true/false            (menos cascatas do sol e distância de sombra menor:
                                            sombra_cascatas 1..4, padrão 3; sombra_distancia 1000..20000, padrão 10000)
  motion_blur: true/false                  (false aplica o patch "sem motion blur")
  reflexos: true/false                     (false aplica o patch "sem SSR")
  destravar_fps: true/false                (desliga a trava de 30 fps do jogo)
  nevoa_densa: true/false                  (névoa 2x mais densa pra esconder o corte; método global, em teste)
  lod_escala: float, faixas_longas, faixa5_reduzida, lod_envio_original: true/false  (experimentos: separar a escala global das faixas 5 e 6)
  horizonte: true/false                    (raio dos blocos da cidade acompanha a distância; testado)
  audio_ingles: true/false                 (vozes em inglês com textos no idioma do sistema; testado 2026-10-19)
  particulas_orcamento: 2000 | 256 | 128 | 64  (limite de emissores que já pararam de emitir mas ainda têm
                                            partículas vivas; acima dele os mais velhos somem; 2000 = original)
  particulas: 1.0 | 0.75 | 0.5             (multiplicador padrão de quantas partículas cada efeito solta)
  chuva_distancia: 10000 | 5000 | 3000   (alcance do mapa de oclusão da chuva, CSM1_RAIN_SHADOW_DISTANCE; menor =
                                            menos desenhos no passe de profundidade 1024²; 10000 = original)
  texturas: 0 | 1 | 2                       (viés de mip do emulador: original, metade, um quarto; vai pro
                                            custom_configs/CUSA00004.json como GPU.texture_lod_bias)
Endereços = va do eboot + 0x400000; detalhes em ../re/README.md."""
import json
import os
import struct
import sys

PADRAO = {"resolucao": 720, "distancia": 70, "sombras_reduzidas": True, "motion_blur": False,
          "reflexos": False, "destravar_fps": True, "texturas": 0, "nevoa_densa": False, "horizonte": True,
          "audio_ingles": True}


def f32(v):
    return struct.pack("<f", float(v)).hex()


def u32(v):
    return struct.pack("<I", int(v)).hex()


def bloco(nome, linhas, ligado=True):
    ls = "".join(f'      <Line Type="bytes" Address="{a}" Value="{v}"/>\n' for a, v in linhas)
    return (f'  <Metadata Title="inFAMOUS" Name="{nome}" Note="steam-deck/projetos/infamous" '
            f'Author="Kewin + Claude" PatchVer="2.0" AppVer="01.07" AppElf="eboot.bin" '
            f'isEnabled="{"true" if ligado else "false"}">\n    <PatchList>\n{ls}    </PatchList>\n  </Metadata>\n')


def patches(o):
    out = []
    # Resolução (v3): inicialização 0x5eff00; o bloco do Pro em 0x5f0120 vira "saída e render = LxA".
    res = int(o.get("resolucao", 720))
    if res in (1200, 1000, 900, 800, 720, 600, 540):
        # 800: tela do Deck em 16:10 (1280x800), sem as barras do 16:9 (experimento: a câmera precisa
        # seguir a proporção, senão a imagem estica).
        w, h = {1200: (1920, 1200), 1000: (1600, 1000), 900: (1600, 900), 800: (1280, 800), 720: (1280, 720),
                600: (960, 600), 540: (960, 540)}[res]
        cave = "c703" + u32(w) + "c74304" + u32(h) + "c7430c" + u32(w) + "c74310" + u32(h) + \
               "4889dfe8cd100000e99b020000"
        out.append(bloco(f"Resolucao {res}p", [("0x5f011a", "660f1f440000"), ("0x5f0120", cave)]))
        if res in (1200, 1000, 800, 600) and o.get("tela_virtual_1610", True):  # 16:10 (tela do Deck)
            # Tela virtual do jogo (0x1d0ccc0/0x1d0ccc4 = 1920x1080 fixos em 0x1f03f8): a câmera tira a proporção dela
            # (0x580317) e a cena saía esticada 11% na vertical em 16:10 (logo do DUP oval, 2026-10-20). Altura
            # virtual 1200 = 16:10; as margens de área segura do HUD saem dela também.
            # Legendas (CSubtitleMgr): a base sai de 0x503360 como margem segura - altura/2, mas o texto é desenhado
            # numa projeção de altura fixa 1080; com a altura virtual 1200 a base caía 60 abaixo da borda (1 linha
            # sumia, 2 linhas mostravam só a de cima, 2026-10-20). Lá a altura passa a ser 1080 fixo
            # (lea+mov eax,[0x1d0ccc4] -> mov eax,1080 + nops).
            out.append(bloco("Tela virtual 1920x1200 (16:10)", [
                ("0x5f03f8", "41c707b0040000"),
                ("0x903399", "b838040000" + "90" * 4)]))
    # Tamanho da legenda: as seis funções de layout do CSubtitleMgr passam 36.0 (corpo da fonte) pro texto e
    # quebram a linha em 0.6 x largura segura. Corpo maior pede linha mais larga (até 0.8) pra não virar 4 linhas.
    leg = int(o.get("legenda_tamanho", 36))
    if leg != 36:
        larg = min(0.8, 0.6 * (1 + (leg - 36) / 36 * 0.6))
        out.append(bloco(f"Legenda {leg}", [(hex(0x400000 + a), f32(leg)) for a in
                                            (0xadf87c, 0xadf888, 0xadf894, 0xadf8a0, 0xadf8ac, 0xadf8d8)] +
                         [(hex(0x400000 + a), f32(larg)) for a in
                          (0xadf878, 0xadf884, 0xadf890, 0xadf89c, 0xadf8a8, 0xadf8d4)]))
    # Ligação no alto-falante do controle (como no PS4; o port toca essa porta só no alto-falante direito). O motor de
    # som escolhe a saída pelo "ouvinte" do estilo de fala: dialogue_cell_out/_iso têm alvo no controle, o
    # dialogue_cell simples não (som_celular.txt da RE). 0x4838a0 toca a fala com o estilo em rbx; quando 0x537e40
    # reconhece um estilo de celular (jne em 0x48391b), a cave 0x4832d0 (16 bytes de nop entre funções) troca o estilo
    # pelo hash de dialogue_cell_out e segue pro mesmo destino 0x4839cd.
    if o.get("ligacao_controle", False):
        out.append(bloco("Ligacao no controle", [("0x88391b", "0f85aff9ffff"),
                                                 ("0x8832d0", "48bb801f1b9f74839d8de9ee060000")]))
    # FOV (campo de visão): a câmera 0x580e80 faz tan(fov * 0.5) com a constante 0.5 de 0xae4478 (só essa função usa)
    # e guarda em [cam+0x5a4] (x proporção da tela em +0x5a0). As duas multiplicações do tan (0x580eb2 e 0x580f79)
    # passam a ler 0.5 x fator de 0xaaba40 (presets sem uso, depois da tabela das instâncias). fov 90 = 10% menor:
    # tudo maior na tela, menos coisa no quadro.
    fov = int(o.get("fov", 100))
    if fov != 100:
        k = 0.5 * max(20, min(150, fov)) / 100.0
        # Os setters de FOV 0x580580 (cópia entre câmeras) e 0x5810c0 têm o 0.5 em 0xae446c e 0xae448c: sem eles a
        # câmera do jogo não mudava (o 0x580e80 só recalcula em transição). Os quatro leem 0xaaba40.
        out.append(bloco(f"FOV {fov}%", [("0xeaba40", f32(k)), ("0x980eb2", "c5f2590586ab5200"),
                                         ("0x980f79", "c5fa5905bfaa5200"), ("0x9805b1", "c5fa590587b45200"),
                                         ("0x9810df", "c5fa590559a95200")]))
    # Distância: escala global (escada[0].campo0, 1.0 = 100%) e faixas longas 5 e 6 (6000 e 15000 m).
    p = max(30, min(100, int(o.get("distancia", 70)))) / 100.0
    if p < 0.999:
        faixa5 = 6000.0 * (p ** 1.2)
        faixa6 = max(faixa5 + 500.0, 15000.0 * (p ** 2.3))
        if o.get("faixa6"):  # experimento: corte longe fixo (impostores do horizonte e geometria distante)
            faixa6 = max(faixa5 + 500.0, float(o["faixa6"]))
        # Raio dos blocos da cidade (passe por vista 0x45c090: w = min(1, (R - d) * k), bloco some com w <= 0):
        # original R = 15000 e k = 0.0002 (fade de 5000 m). Acompanha a faixa longa, com fade de 30% de R.
        # Escala global das faixas de LOD: só metade da redução (70% -> 0.85). Com a escala cheia, objetos a poucos
        # metros ficavam na versão simplificada em lugares fechados (relato do Kewin, 2026-10-20; no Alto não acontece).
        escala = float(o.get("lod_escala", 1.0 - (1.0 - p) * 0.5))
        linhas = [("0x11a08c0", f32(escala))]
        # Faixas longas 5 e 6 encurtadas. O corte (0x1d2e80) escolhe o LOD pela distância até a CAIXA do objeto, mas a
        # conferência do envio (0x1ec170) mede até o PIVÔ e descarta a malha se d >= s·faixa[hi+1]: peças grandes
        # como o píer do mapa novo (pivô a ~80 m com o Delsin em cima) sumiam com a faixa 6 em 6600 (A/B no mesmo
        # ponto, 2026-10-20). Correção abaixo: o limite superior dessa conferência lê a tabela original.
        # O chão do píer (tábuas instanciadas, M-1D24 no modo inspeção) sumia pelo coletor de instâncias, não pelo
        # envio: resolvido com a tabela própria do coletor abaixo (instancias_faixa6 = 10000, aprovado em 2026-10-20:
        # píer ok no ponto ruim, sessão com média de 43 FPS e ~2.300 desenhos/quadro).
        if o.get("faixa5_reduzida", True):
            linhas.append(("0x11faa44", f32(faixa5)))
        if o.get("faixas_longas", True):
            linhas.append(("0x11faa48", f32(faixa6)))
            if o.get("lod_envio_original", True):
                # Limite superior da conferência do envio lê o preset sem uso 0xaab9e0 = {400, 750, 1500, 3500, 6000,
                # 15000, 999999, ...} = faixa original deslocada de 1. rcx = tabela 0xdfaa30 (lea intacto), então
                # [rcx + rax*4 - 0x34f050] = preset[hi] = faixa_original[hi+1]. Relativo: o jogo carrega em
                # 0x800000000, não em 0x400000 (a 1ª versão com endereço absoluto travou na tela preta, SD-015).
                # 0x1ec2d1: movsxd rax,esi; jmp 0x1ec8c0; nop. Caverna 0x1ec8c0 (16 B de nop depois do call de
                # stack-check da mesma função): vmulss xmm0,xmm0,[rcx+rax*4-0x34f050]; jmp 0x1ec2da.
                out.append(bloco("LOD: envio confere o limite pela faixa original (pecas grandes perto)", [
                    ("0x5ec2d1", "4863c6e9e705000090"),
                    ("0x5ec8c0", "c5fa598481b00fcbffe90cfaffff"),
                    # Mesma conferência por pedaço da malha, nos dois laços da função (o chão do píer caía aqui):
                    # o lea do limite superior só serve a ele; aponta pra preset - 4 (0xaab9dc).
                    ("0x5ec6f7", "488d0ddef28b00"),
                    ("0x5ec81d", "488d0db8f18b00"),
                    # Predicado 0x1e97c0 (mesma conta, rsi = tabela p/ os dois limites): caverna 0x1e8570 (16 B de
                    # nop depois do call de stack-check): vmulss xmm1,xmm1,[rsi+rcx*4-0x34f050]; jmp 0x1e9804.
                    ("0x5e97fe", "e96dedffff90"),
                    ("0x5e8570", "c5f2598c8eb00fcbffe986120000")]))
            # Coletor de instâncias 0x435820 (tábuas do píer, grupos instanciados): monta limites s·T[1..7] pra
            # 0x58d240, que mede da câmera ao CENTRO do grupo (um ponto, sem raio). É o corte que mais tira desenhos
            # (com a tabela original: ~8.000/quadro contra ~1.500), mas grupos grandes somem com o Delsin em cima.
            # Tabela própria em 0xaaba20 (presets sem uso, sem referência), faixa 6 num meio-termo ajustável.
            inst6 = o.get("instancias_faixa6", 10000.0)
            if inst6 is not None:
                t = [0.0, 400.0, 750.0, 1500.0, 3500.0, faixa5 if o.get("faixa5_reduzida", True) else 6000.0,
                     max(float(inst6), faixa6), 3.4e38]
                out.append(bloco(f"LOD: instancias ate {int(t[6])} (tabela propria do coletor)", [
                    ("0xeaba20", "".join(f32(x) for x in t)),
                    ("0x835904", "488d0d15616700")]))
        if o.get("horizonte", True):
            # Testado em 2026-10-15 (E18a): impostores de 4,7k pra 2,5k/quadro, sem efeito colateral.
            # Raio dos blocos nunca abaixo de 10000 (~100 m): com 6600 (distância 70%) prédios ao lado viravam cartão
            # em alguns lugares (relato do Kewin, 2026-10-20).
            raio = max(10000.0, faixa6)
            if o.get("horizonte_raio"):  # experimento: raio dos blocos fixo (corte dos impostores)
                raio = max(1000.0, float(o["horizonte_raio"]))
            k = 1.0 / max(500.0, raio * 0.3)
            linhas += [("0xd8b224", f32(raio)), ("0xd8b228", f32(k))]
        out.append(bloco(f"Distancia de desenho {int(p * 100)}%", linhas))
    if o.get("nevoa_densa", False) and p < 0.999:
        # Constante global 100000 do HAZE_DENSITY (setter/getter dividem por ela, 0xd9adc0): 50000 dobra a
        # densidade de todos os níveis. (A versão por registrador em 0x51e2d1 deu tela preta: SD-013.)
        out.append(bloco("Nevoa mais densa (esconde o corte)", [("0xd9adc0", "0050c347".replace("0050c347", "00504347"))]))
    if o.get("sombras_reduzidas", True):
        # Cascatas do sol (original 4) e distância das sombras do sol (unidade do jogo: 20000 = 200 m original).
        # O mapa de sombra do sol é ~52% dos desenhos do quadro na rua padrão (captura de 2026-10-19).
        cascatas = max(1, min(4, int(o.get("sombra_cascatas", 3))))
        dist = max(1000.0, min(20000.0, float(o.get("sombra_distancia", 10000))))
        out.append(bloco(f"Sombras reduzidas ({cascatas} cascatas, {int(dist / 100)} m)",
                         [("0x11f9d24", u32(cascatas)),
                          ("0x66ea1f", "c5f057c9c5fa1010c5f2c2c801c4e3694ac010c5fa5dc2c3"),
                          ("0x11f9d1c", f32(dist))]))
    chuva = float(o.get("chuva_distancia", 10000))
    if chuva < 9999:
        # float global 0xdf9d20 (va; dados) = 10000: limite de longe da única cascata do mapa de oclusão da chuva
        # (passe 1024² montado em 0x43b7b0). nativo/passes.md.
        out.append(bloco(f"Chuva: oclusao ate {int(chuva / 100)} m", [("0x11f9d20", f32(max(1000.0, chuva)))]))
    if not o.get("motion_blur", False):
        out.append(bloco("Sem motion blur", [("0x593853", "e97b04000090")]))
    if not o.get("reflexos", False):
        out.append(bloco("Sem reflexos SSR", [("0x85a6c5", "e97905000090")]))
    if o.get("audio_ingles", True):
        # va 0x5ea620 monta "lang_%s_%s%s.xpp" (idioma pela tabela 0xd7b500, tipo 7/0x1b = texto, 0x1a/0x1c = áudio).
        # Reescrito pra que os pacotes de áudio usem sempre o índice 1 (english); o texto segue o idioma do sistema.
        out.append(bloco("Audio em ingles", [("0x9ea630", "83fa07742683fa1b742183fa1a740e83fa1c7409488d0d95ea4f00"
                                                         "eb0e488d0d92ea4f00be010000009090")]))
    # Partículas (achado de 2026-10-19, nativo/particulas.md): o custo do especial vem do número de emissores
    # (cada um gera até 3 dispatches de compute e seus desenhos), não de partículas.
    orc = int(o.get("particulas_orcamento", 2000))
    if orc < 2000:
        # int em 0x11f886c (dados, só lido): orçamento de emissores "terminados mas vivos" (CParticleThrottle).
        out.append(bloco(f"Particulas: limite de {orc} efeitos", [("0x11f886c", u32(max(16, orc)))]))
    razao = float(o.get("particulas", 1.0))
    if razao < 0.999:
        # PARTICLE_COUNT_RATIO padrão 1.0 nos dois construtores (0x7f5035 e 0x7f84ba): só o float muda.
        out.append(bloco(f"Particulas: {int(razao * 100)}% da quantidade",
                         [("0x7f503b", f32(razao)), ("0x7f84c2", f32(razao))]))
    if o.get("destravar_fps", True):
        out.append(bloco("Destravar taxa de quadros", [("0x5f2eb7", "c687f80edf0000")]))
    return out


def main():
    pasta = sys.argv[1]
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, "opcoes.json")
    o = dict(PADRAO)
    if os.path.exists(caminho):
        try:
            o.update(json.load(open(caminho, encoding="utf-8")))
        except (OSError, ValueError):
            pass
    json.dump(o, open(caminho, "w", encoding="utf-8"), indent=2)
    # Experimentos: GERAR_EXTRA='{"audio_ingles": false}' muda só esta geração, sem gravar no opcoes.json.
    if os.environ.get("GERAR_EXTRA"):
        o.update(json.loads(os.environ["GERAR_EXTRA"]))
    xml = ('<?xml version="1.0" encoding="utf-8"?>\n<!-- Gerado por gerar.py a partir de opcoes.json; '
           'editar as opções, não este arquivo. -->\n<Patch>\n' + "".join(patches(o)) + "</Patch>\n")
    open(os.path.join(pasta, "inFAMOUS.xml"), "w", encoding="utf-8").write(xml)
    open(os.path.join(pasta, "files.json"), "w", encoding="utf-8").write('{"inFAMOUS.xml": ["CUSA00004", "CUSA00223"]}')
    # Ajuste do emulador (não é patch): viés de mip na configuração do jogo.
    cfg = os.path.join(pasta, "..", "..", "custom_configs", "CUSA00004.json")
    if os.path.exists(cfg):
        try:
            c = json.load(open(cfg, encoding="utf-8"))
            c.setdefault("GPU", {})["texture_lod_bias"] = max(0, min(2, int(o.get("texturas", 0))))
            json.dump(c, open(cfg, "w", encoding="utf-8"), indent=2)
        except (OSError, ValueError) as e:
            print("aviso: custom config:", e)
    print("opcoes:", json.dumps(o), "| patches:", len(patches(o)))


if __name__ == "__main__":
    main()
