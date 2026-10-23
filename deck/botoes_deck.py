#!/usr/bin/env python3
"""Icones de botao do Steam Deck no jogo, gerados a partir dos arquivos do proprio jogador (so biblioteca padrao: roda
no python3 do SteamOS, sem Pillow).

Nos pacotes de texto (art/cache/lang_<idioma>_text.xpps) o jogo guarda os icones de botao num atlas 512x512. Para cada
icone do PS4, este script fecha o recorte do simbolo e recorta no lugar a letra do Deck, com a fonte condensada do
proprio jogo (a das letras de L1/R1), no mesmo estilo dos icones originais:
    cruz -> A, circulo -> B, quadrado -> X, triangulo -> Y, OPTIONS e START -> MENU, touchpad -> PAD.
Ombros, analogicos e direcional ficam iguais. Saida: um mod de arquivos soltos que o port carrega sozinho:
    <mods>/steamdeck-botoes/dvdroot_ps4/art/cache/lang_<idioma>_text.xpps

    python3 botoes_deck.py <pasta do jogo> <pasta mods> [--previa saida.ppm]
"""
from __future__ import annotations

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import texto_xpps as T  # noqa: E402

ICONES_TEX = 0xED955BAC0C1CC129  # atlas dos icones (igual em todos os idiomas)
LETRAS_NOME = 0x9D8EC1C0AF34668E  # fonte condensada e grossa das letras de L1/R1
FONT_CLASS = 0x70AFB83EAAD27A6C
TEX_CLASS = 0xEE8B65DE084738C4
CANAL = {0x000000FF: 0, 0x0000FF00: 1, 0x00FF0000: 2, 0xFF000000: 3}
SS = 4  # supersampling do recorte
TROCAS = [(0xF083, "A", 0.50, 0.6), (0xF080, "B", 0.50, 0.6), (0xF081, "X", 0.50, 0.6), (0xF082, "Y", 0.50, 0.6),
          (0xF088, "MENU", 0.42, 0.78), (0xF089, "MENU", 0.42, 0.78), (0xF0E6, "MENU", 0.42, 0.78),
          (0xF0A2, "PAD", 0.42, 0.78)]


# ---------- leitura do pacote: fontes e texturas ----------
def bits(v, lo, n):
    return (v >> lo) & ((1 << n) - 1)


def fontes(k):
    _li, lt = T.find_links(k)
    out = []
    for local, cls in sorted(lt.cid):
        if cls != FONT_CLASS:
            continue
        o = local - 0x10
        f = dict(name_hash=k.u64(o + 0x18), tex_hash=k.u64(o + 0x28), h1=struct.unpack_from("<HH", k.data, o + 0x34),
                 glyphs=[])
        gptr, n = k.u64(o + 0x38), k.u64(o + 0x40)
        for i in range(n):
            g = gptr + 0x20 * i
            cp, x, y, w, h = struct.unpack_from("<HHHHH", k.data, g)
            mask = struct.unpack_from("<Q", k.data, g + 0x10)[0]
            f["glyphs"].append(dict(cp=cp, x=x, y=y, w=w, h=h, mask=mask))
        out.append(f)
    return out


def texturas(k):
    _li, lt = T.find_links(k)
    out = []
    for local, cls in lt.cid:
        if cls != TEX_CLASS:
            continue
        base = k.items[k.item_of(local)][1]
        w = struct.unpack_from("<8I", k.data, base + 0x28)
        out.append(dict(addr=w[0] | (bits(w[1], 0, 8) << 32), width=bits(w[2], 0, 14) + 1,
                        height=bits(w[2], 14, 14) + 1, pitch=bits(w[4], 13, 14) + 1,
                        name_hash=struct.unpack_from("<Q", k.data, base + 0x48)[0]))
    return out


def elem_index(x, y):  # micro tile 8x8 (Thin1DThin)
    return (x & 1) | ((y & 1) << 1) | ((x & 2) << 1) | ((y & 2) << 2) | ((x & 4) << 2) | ((y & 4) << 3)


def detile(buf, off, w, h, p):
    """Pixels RGBA em linhas, ja virados (o jogo guarda o atlas de cabeca pra baixo; as coordenadas dos glifos
    valem para a imagem virada)."""
    out = bytearray(w * h * 4)
    tpr = (max(8, (p + 7) & ~7)) // 8
    for y in range(h):
        yy = h - 1 - y
        for x in range(w):
            src = off + (((y // 8) * tpr + (x // 8)) * 64 + elem_index(x, y)) * 4
            d = (yy * w + x) * 4
            out[d:d + 4] = buf[src:src + 4]
    return out


def tile(pix, buf, off, w, h, p):
    tpr = (max(8, (p + 7) & ~7)) // 8
    for y in range(h):
        yy = h - 1 - y
        for x in range(w):
            dst = off + (((y // 8) * tpr + (x // 8)) * 64 + elem_index(x, y)) * 4
            s = (yy * w + x) * 4
            buf[dst:dst + 4] = pix[s:s + 4]


# ---------- mascaras em tons de cinza (listas de linhas de ints 0..255) ----------
def canal(pix, w, x0, y0, cw, ch, c):
    return [[pix[((y0 + y) * w + x0 + x) * 4 + c] for x in range(cw)] for y in range(ch)]


def filtro3(m, fn):
    h, w = len(m), len(m[0])
    return [[fn(m[yy][xx] for yy in range(max(0, y - 1), min(h, y + 2)) for xx in range(max(0, x - 1), min(w, x + 2)))
             for x in range(w)] for y in range(h)]


def limiar(m, t):
    return [[255 if v > t else 0 for v in row] for row in m]


def redimensiona(m, nw, nh):
    """Area (media dos pixels cobertos) ao reduzir, bilinear ao ampliar."""
    h, w = len(m), len(m[0])
    if nw <= 0 or nh <= 0:
        return [[0]]
    out = []
    for y in range(nh):
        sy0, sy1 = y * h / nh, (y + 1) * h / nh
        linha = []
        for x in range(nw):
            sx0, sx1 = x * w / nw, (x + 1) * w / nw
            if sx1 - sx0 >= 1 and sy1 - sy0 >= 1:
                tot = area = 0.0
                for yy in range(int(sy0), min(h, int(sy1 + 0.999))):
                    fy = min(yy + 1, sy1) - max(yy, sy0)
                    for xx in range(int(sx0), min(w, int(sx1 + 0.999))):
                        f = fy * (min(xx + 1, sx1) - max(xx, sx0))
                        tot += m[yy][xx] * f
                        area += f
                linha.append(int(tot / area + 0.5) if area else 0)
            else:
                fx = max(0.0, min(w - 1.0, (x + 0.5) * w / nw - 0.5))
                fy = max(0.0, min(h - 1.0, (y + 0.5) * h / nh - 0.5))
                x0, y0 = int(fx), int(fy)
                x1, y1 = min(w - 1, x0 + 1), min(h - 1, y0 + 1)
                ax, ay = fx - x0, fy - y0
                v = (m[y0][x0] * (1 - ax) + m[y0][x1] * ax) * (1 - ay) + (m[y1][x0] * (1 - ax) + m[y1][x1] * ax) * ay
                linha.append(int(v + 0.5))
        out.append(linha)
    return out


def fecha(alpha):
    """Preenche os recortes internos: tudo que nao e alcancavel pela borda vira cheio."""
    h, w = len(alpha), len(alpha[0])
    cheio = [[v > 24 for v in row] for row in alpha]
    fora = [[False] * w for _ in range(h)]
    pilha = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while pilha:
        x, y = pilha.pop()
        if 0 <= x < w and 0 <= y < h and not fora[y][x] and not cheio[y][x]:
            fora[y][x] = True
            pilha += ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
    return [[max(alpha[y][x], 0 if fora[y][x] else 255) for x in range(w)] for y in range(h)]


# ---------- os icones ----------
class Gerador:
    def __init__(self, pacote):
        self.k = T.Kcap(open(pacote, "rb").read())
        fs = fontes(self.k)
        self.icones = next(f for f in fs if f["tex_hash"] == ICONES_TEX)
        letras = next((f for f in fs if f["name_hash"] == LETRAS_NOME), None)
        if letras is None:  # russo: fontes proprias; a de linha mais alta e a condensada grossa
            cands = [f for f in fs if f["tex_hash"] != ICONES_TEX and
                     all(any(g["cp"] == ord(c) and g["w"] for g in f["glyphs"]) for c in "ABXYMENUPD")]
            letras = max(cands, key=lambda f: f["h1"][0])
        self.letras = letras
        self.tex = {t["name_hash"]: t for t in texturas(self.k)}

    def atlas(self, h):
        t = self.tex[h]
        return t, detile(self.k.data, t["addr"], t["width"], t["height"], t["pitch"])

    def glifo(self, fonte, cp):
        return next(g for g in fonte["glyphs"] if g["cp"] == cp)

    def letra(self, pix, w, ch):
        g = self.glifo(self.letras, ord(ch))
        m = canal(pix, w, g["x"], g["y"], g["w"], g["h"], CANAL.get(g["mask"], 3))
        m = filtro3(filtro3(m, max), min)  # tira a textura gasta: fecha buracos pequenos
        return limiar(m, 110)

    def texto(self, pix, w, txt, altura):
        pecas = [self.letra(pix, w, c) for c in txt]
        esc = altura / max(len(p) for p in pecas)
        esp = int(0.06 * altura)
        ws = [max(1, int(len(p[0]) * esc)) for p in pecas]
        out = [[0] * (sum(ws) + esp * (len(txt) - 1)) for _ in range(altura)]
        x = 0
        for p, pw in zip(pecas, ws):
            r = redimensiona(p, pw, altura)
            for y in range(altura):
                out[y][x:x + pw] = r[y]
            x += pw + esp
        return out

    def gera(self):
        t_ic, icone = self.atlas(ICONES_TEX)
        _t_le, letras = self.atlas(self.letras["tex_hash"])
        wl = _t_le["width"]
        W = t_ic["width"]
        for cp, txt, alt_rel, larg_max in TROCAS:
            g = next((g for g in self.icones["glyphs"] if g["cp"] == cp), None)
            if not g or not g["w"]:
                continue
            a = canal(icone, W, g["x"], g["y"], g["w"], g["h"], 3)
            base = redimensiona(fecha(a), g["w"] * SS, g["h"] * SS)
            alt = int(g["h"] * alt_rel * SS)
            tm = self.texto(letras, wl, txt, alt)
            if len(tm[0]) > larg_max * g["w"] * SS:
                f = larg_max * g["w"] * SS / len(tm[0])
                tm = redimensiona(tm, int(len(tm[0]) * f), max(1, int(len(tm) * f)))
            th, tw = len(tm), len(tm[0])
            ox, oy = (g["w"] * SS - tw) // 2, (g["h"] * SS - th) // 2
            for y in range(th):
                linha = base[oy + y]
                for x in range(tw):
                    linha[ox + x] = linha[ox + x] * (255 - tm[y][x]) // 255
            novo = redimensiona(base, g["w"], g["h"])
            for y in range(g["h"]):
                for x in range(g["w"]):
                    d = ((g["y"] + y) * W + g["x"] + x) * 4
                    icone[d:d + 4] = bytes((255, 255, 255, novo[y][x]))
        tile(icone, self.k.data, t_ic["addr"], t_ic["width"], t_ic["height"], t_ic["pitch"])
        self.icone_novo, self.W = icone, W
        return self.k.serialize()

    def previa(self, caminho):
        """PPM com os icones trocados sobre fundo escuro (conferencia)."""
        cel = 72
        cps = [c[0] for c in TROCAS]
        img = bytearray(bytes((40, 40, 60)) * (cel * len(cps) * cel))
        for i, cp in enumerate(cps):
            g = self.glifo(self.icones, cp)
            for y in range(min(g["h"], cel)):
                for x in range(min(g["w"], cel)):
                    s = ((g["y"] + y) * self.W + g["x"] + x) * 4
                    a = self.icone_novo[s + 3] / 255
                    d = ((y + 4) * cel * len(cps) + i * cel + x + 4) * 3
                    if d + 3 <= len(img):
                        for c in range(3):
                            img[d + c] = int(img[d + c] * (1 - a) + self.icone_novo[s + c] * a)
        with open(caminho, "wb") as f:
            f.write(b"P6 %d %d 255\n" % (cel * len(cps), cel) + bytes(img))


def main():
    jogo, mods = sys.argv[1], sys.argv[2]
    cache = os.path.join(jogo, "art", "cache")
    destino = os.path.join(mods, "steamdeck-botoes", "dvdroot_ps4", "art", "cache")
    os.makedirs(destino, exist_ok=True)
    feitos = 0
    for nome in sorted(os.listdir(cache)):
        if not (nome.startswith("lang_") and nome.endswith("_text.xpps")):
            continue
        try:
            g = Gerador(os.path.join(cache, nome))
            dados = g.gera()
        except (StopIteration, KeyError, T.FormatoErro, struct.error) as e:
            print(f"{nome}: pulado ({e!r})", flush=True)
            continue
        tmp = os.path.join(destino, nome + ".novo")
        with open(tmp, "wb") as f:
            f.write(dados)
        os.replace(tmp, os.path.join(destino, nome))
        feitos += 1
        print(f"{nome}: ok", flush=True)
        if "--previa" in sys.argv and nome == "lang_english_text.xpps":
            g.previa(sys.argv[sys.argv.index("--previa") + 1])
    print(f"icones do Deck: {feitos} idiomas em {destino}")
    return 0 if feitos else 1


if __name__ == "__main__":
    sys.exit(main())
