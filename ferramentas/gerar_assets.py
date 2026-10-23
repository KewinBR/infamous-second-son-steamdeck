"""Gera as imagens prontas do instalador (instalador/assets/) a partir de arte/. Roda no PC de desenvolvimento
(precisa de Pillow); o Deck so le os PNG (o Tk do SteamOS nao tem Pillow). Tela do Deck: 1280x800.

    python ferramentas/gerar_assets.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
ARTE = RAIZ / "arte"
SAIDA = RAIZ / "instalador" / "assets"
W, H = 1280, 800
AMARELO = (242, 183, 30, 255)


def cobrir(img, w, h, puxa=0.35):
    """Cobre w x h sem distorcer, com o recorte puxado pra esquerda (o assunto fica a direita)."""
    sc = max(w / img.width, h / img.height)
    a = img.resize((round(img.width * sc), round(img.height * sc)), Image.LANCZOS)
    x = int((a.width - w) * puxa)
    y = (a.height - h) // 2
    return a.crop((x, y, x + w, y + h))


def sombras(img, escurece=0.0):
    """Sombra da esquerda (o texto fica ali) e de baixo, como na tela de abertura do port."""
    img = img.convert("RGBA")
    ov = Image.new("RGBA", img.size)
    d = ImageDraw.Draw(ov)
    for i in range(W):
        t = max(0.0, 1 - i / (W * 0.72))
        d.line([(i, 0), (i, H)], fill=(6, 7, 9, int(245 * min(1.0, t * 1.25) ** 0.7)))
    for j in range(H):
        t = max(0.0, (j - H * 0.55) / (H * 0.45))
        d.line([(0, j), (W, j)], fill=(6, 7, 9, int(200 * t)))
    img.alpha_composite(ov)
    if escurece:
        img.alpha_composite(Image.new("RGBA", img.size, (6, 7, 9, int(255 * escurece))))
    return img.convert("RGB")


def logo(nome, largura):
    lg = Image.open(ARTE / nome).convert("RGBA")
    return lg.resize((largura, round(lg.height * largura / lg.width)), Image.LANCZOS)


def card(w, h, sel):
    img = Image.new("RGBA", (w, h), (14, 15, 18, 215 if sel else 170))
    d = ImageDraw.Draw(img)
    if sel:
        d.rectangle([0, 0, w - 1, h - 1], outline=AMARELO, width=2)
        d.rectangle([0, 0, 5, h - 1], fill=AMARELO)
    return img


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    delsin = Image.open(ARTE / "delsin-steamdeck.png").convert("RGB")
    neon = Image.open(ARTE / "neon-steamdeck.jpg").convert("RGB")
    sombras(cobrir(delsin, W, H)).save(SAIDA / "fundo-inicio.png", optimize=True)
    sombras(cobrir(delsin, W, H), 0.15).save(SAIDA / "fundo-passos.png", optimize=True)
    sombras(cobrir(delsin, W, H), 0.25).save(SAIDA / "fundo-instalando.png", optimize=True)
    sombras(cobrir(neon, W, H)).save(SAIDA / "fundo-pronto.png", optimize=True)
    logo("logo-vertical.png", 420).save(SAIDA / "logo-vertical.png", optimize=True)
    logo("logo-horizontal.png", 250).save(SAIDA / "logo-horizontal.png", optimize=True)
    logo("logo-horizontal.png", 360).save(SAIDA / "logo-horizontal-360.png", optimize=True)
    for w, h in [(700, 92), (340, 92), (700, 100), (520, 64)]:
        for sel in (False, True):
            card(w, h, sel).save(SAIDA / f"card-{w}x{h}{'-sel' if sel else ''}.png", optimize=True)
    steam(delsin)
    print("assets em", SAIDA)


def steam(delsin):
    """Artes da biblioteca da Steam (config/grid): capa vertical 600x900, horizontal 920x430, fundo do topo
    1920x620, logo transparente e icone 256x256."""
    pasta = SAIDA / "steam"
    pasta.mkdir(exist_ok=True)
    lv = Image.open(ARTE / "logo-vertical.png").convert("RGBA")
    lh = Image.open(ARTE / "logo-horizontal.png").convert("RGBA")

    def com_logo(fundo, lg, largura, x, y):
        img = fundo.convert("RGBA")
        l2 = lg.resize((largura, round(lg.height * largura / lg.width)), Image.LANCZOS)
        img.alpha_composite(l2, (x if x >= 0 else (img.width - l2.width) // 2, y if y >= 0 else img.height - l2.height + y))
        return img.convert("RGB")

    def sombra_baixo(img, forca=0.85, inicio=0.45):
        img = img.convert("RGBA")
        ov = Image.new("RGBA", img.size)
        d = ImageDraw.Draw(ov)
        for j in range(img.height):
            t = max(0.0, (j - img.height * inicio) / (img.height * (1 - inicio)))
            d.line([(0, j), (img.width, j)], fill=(6, 7, 9, int(255 * forca * t)))
        img.alpha_composite(ov)
        return img

    def sombra_esq(img, forca=0.9, ate=0.6):
        img = img.convert("RGBA")
        ov = Image.new("RGBA", img.size)
        d = ImageDraw.Draw(ov)
        for i in range(img.width):
            t = max(0.0, 1 - i / (img.width * ate))
            d.line([(i, 0), (i, img.height)], fill=(6, 7, 9, int(255 * forca * t)))
        img.alpha_composite(ov)
        return img

    capa = sombra_baixo(cobrir(delsin, 600, 900, 0.72), 1.0, 0.25)
    com_logo(capa, lv, 470, -1, -40).save(pasta / "capa.png", optimize=True)
    horiz = sombra_esq(cobrir(delsin, 920, 430, 0.35), 0.9, 0.62)
    com_logo(horiz, lh, 400, 40, -1 if False else (430 - round(lh.height * 400 / lh.width)) // 2).save(
        pasta / "horizontal.png", optimize=True)
    cobrir(delsin, 1920, 620, 0.35).save(pasta / "fundo.png", optimize=True)
    lh.resize((1280, round(lh.height * 1280 / lh.width)), Image.LANCZOS).save(pasta / "logo.png", optimize=True)
    ic = Image.new("RGBA", (256, 256), (12, 12, 14, 255))
    esc = min(236 / lv.width, 236 / lv.height)
    lv2 = lv.resize((round(lv.width * esc), round(lv.height * esc)), Image.LANCZOS)
    ic.alpha_composite(lv2, ((256 - lv2.width) // 2, (256 - lv2.height) // 2))
    ic.save(pasta / "icone.png", optimize=True)


if __name__ == "__main__":
    main()
