"""Video tutorial de instalacao (ilustrativo, nao gravado ao vivo): o Deck desenhado no meio, o passo em cima, toques
animados e as telas de verdade do instalador (capturadas com DEMO=1 PRINTS=... TELAS=... PROGRESSO_DEMO=...).

    python ferramentas/video_tutorial.py <pasta das telas do instalador> <saida.mp4> [pt|en]
"""
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
FONTES = RAIZ / "instalador" / "fontes"
ARTE = RAIZ / "arte"
STEAM = RAIZ / "instalador" / "assets" / "steam"
TELAS = Path(sys.argv[1])
SAIDA = Path(sys.argv[2])
L = sys.argv[3] if len(sys.argv) > 3 else "pt"
W, H, FPS = 1920, 1080, 30
AM = (242, 183, 30)
BR = (235, 233, 226)
CI = (160, 160, 160)
TIT = lambda s: ImageFont.truetype(str(FONTES / "ISSDeckStencil.ttf"), s)
REG = lambda s: ImageFont.truetype(str(FONTES / "Barlow-Regular.ttf"), s)
MED = lambda s: ImageFont.truetype(str(FONTES / "Barlow-Medium.ttf"), s)
BOL = lambda s: ImageFont.truetype(str(FONTES / "Barlow-Bold.ttf"), s)

TX = {
    "intro": ("COMO INSTALAR NO STEAM DECK", "HOW TO INSTALL ON THE STEAM DECK"),
    "intro_sub": ("Sem teclado e sem mouse. Você só precisa da sua cópia do jogo.",
                  "No keyboard, no mouse. You only need your own copy of the game."),
    "passo": ("PASSO {} DE 8", "STEP {} OF 8"),
    "t1": ("COPIE OS .PKG DO SEU JOGO", "COPY YOUR GAME'S .PKG FILES"),
    "s1": ("O jogo base e a atualização 1.07, pro cartão microSD ou pra pasta Downloads.",
           "The base game and the 1.07 update, to the microSD card or the Downloads folder."),
    "t2": ("MUDE PARA O MODO DESKTOP", "SWITCH TO DESKTOP MODE"),
    "s2": ("Segure o botão de ligar e escolha Mudar para a Área de Trabalho.",
           "Hold the power button and choose Switch to Desktop."),
    "t3": ("BAIXE O INSTALADOR", "DOWNLOAD THE INSTALLER"),
    "s3": ("No navegador, abra a página de releases do projeto e baixe Instalar-inFAMOUS.desktop.",
           "In the browser, open the project's releases page and download Instalar-inFAMOUS.desktop."),
    "t4": ("ABRA O ARQUIVO", "OPEN THE FILE"),
    "s4": ("Na pasta Downloads, toque duas vezes nele e confirme.",
           "In the Downloads folder, tap it twice and confirm."),
    "t5": ("O INSTALADOR ACHA O JOGO", "THE INSTALLER FINDS THE GAME"),
    "s5": ("Ele acha os .pkg sozinho e já marca o jogo e a atualização.",
           "It finds the .pkg files by itself and checks the game and the update."),
    "t6": ("ESCOLHA ONDE INSTALAR", "CHOOSE WHERE TO INSTALL"),
    "s6": ("SSD (carrega mais rápido) ou cartão microSD. Precisa de 32 GB livres.",
           "SSD (faster loading) or microSD card. Needs 32 GB free."),
    "t7": ("ESPERE A INSTALAÇÃO", "WAIT FOR THE INSTALLATION"),
    "s7": ("Uns 10 a 20 minutos. Deixe o Deck na tomada.", "About 10 to 20 minutes. Keep the Deck plugged in."),
    "t8": ("JOGUE PELO MODO DE JOGO", "PLAY FROM GAME MODE"),
    "s8": ("Volte ao Modo de Jogo: o jogo está na biblioteca, com capa e ícone.",
           "Go back to Game Mode: the game is in your library, with cover art and icon."),
    "fim_sub": ("Port para Steam Deck por Kewin Lima", "Steam Deck port by Kewin Lima"),
    "f_pasta": ("Cartão microSD  ›  ps4", "microSD card  ›  ps4"),
    "f_down": ("Downloads", "Downloads"),
    "m_susp": ("Suspender", "Sleep"), "m_rein": ("Reiniciar", "Restart"), "m_desl": ("Desligar", "Shut Down"),
    "m_desk": ("Mudar para a Área de Trabalho", "Switch to Desktop"), "m_tit": ("ENERGIA", "POWER"),
    "dlg": ("Executar este arquivo?", "Run this file?"), "dlg_ok": ("Continuar", "Continue"),
    "dlg_no": ("Cancelar", "Cancel"), "jogar": ("JOGAR", "PLAY"),
    "carregando": ("PREPARANDO OS SHADERS", "PREPARING SHADERS"),
}


def t(k):
    return TX[k][0 if L == "pt" else 1]


# ---------- telas ilustrativas (1280x800, o tamanho da tela do Deck) ----------
def tela_vazia(cor=(22, 24, 28)):
    return Image.new("RGB", (1280, 800), cor)


def janela(img, titulo):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1280, 48], fill=(40, 42, 48))
    d.text((24, 12), titulo, font=MED(22), fill=BR)
    for i, c in enumerate(((230, 80, 70), (230, 180, 60), (90, 190, 90))):
        d.ellipse([1180 + i * 30, 16, 1196 + i * 30, 32], fill=c)


def icone_arquivo(d, x, y, nome, sub, destaque=False):
    if destaque:
        d.rounded_rectangle([x - 14, y - 14, x + 214, y + 214], 12, fill=(52, 70, 92))
    d.rounded_rectangle([x + 50, y, x + 150, y + 120], 8, fill=(230, 230, 232))
    d.polygon([(x + 120, y), (x + 150, y + 30), (x + 120, y + 30)], fill=(190, 190, 194))
    d.rectangle([x + 62, y + 70, x + 138, y + 98], fill=AM)
    d.text((x + 100, y + 84), sub, font=BOL(18), fill=(20, 20, 22), anchor="mm")
    lin = nome if len(nome) < 22 else nome[:21] + "\n" + nome[21:]
    d.multiline_text((x + 100, y + 136), lin, font=MED(19), fill=BR, anchor="ma", align="center")


def tela_arquivos():
    img = tela_vazia()
    janela(img, t("f_pasta"))
    d = ImageDraw.Draw(img)
    icone_arquivo(d, 120, 160, "Infamous Second son.pkg", "PKG")
    icone_arquivo(d, 400, 160, "inFAMOUS Second Son-up.pkg", "PKG")
    d.text((120, 470), "24,1 GB  •  3,9 GB" if L == "pt" else "24.1 GB  •  3.9 GB", font=REG(22), fill=CI)
    return img


def tela_energia(sel=False):
    img = Image.open(ARTE / "delsin-steamdeck.png").convert("RGB").resize((1280, 720)).crop((0, 0, 1280, 720))
    img = img.resize((1280, 800)).filter(ImageFilter.GaussianBlur(14))
    img = Image.blend(img, Image.new("RGB", img.size, (10, 10, 12)), 0.6)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([390, 180, 890, 640], 14, fill=(30, 32, 38))
    d.text((430, 210), t("m_tit"), font=BOL(24), fill=CI)
    for i, k in enumerate(("m_susp", "m_rein", "m_desl", "m_desk")):
        y = 270 + i * 88
        if k == "m_desk" and sel:
            d.rounded_rectangle([410, y - 10, 870, y + 62], 10, fill=(60, 66, 78))
        d.text((440, y + 6), t(k), font=MED(28), fill=BR)
    return img


def tela_navegador(sel=False):
    img = tela_vazia((246, 247, 249))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1280, 70], fill=(225, 228, 233))
    d.rounded_rectangle([120, 16, 1160, 54], 19, fill=(255, 255, 255))
    d.text((150, 25), "github.com/KewinBR/infamous-second-son-steamdeck/releases", font=REG(20), fill=(60, 60, 70))
    lg = Image.open(ARTE / "logo-horizontal.png").convert("RGBA")
    lg = lg.resize((300, int(lg.height * 300 / lg.width)))
    escuro = Image.new("RGB", (1280, 150), (18, 18, 20))
    escuro.paste(lg, (60, (150 - lg.height) // 2), lg)
    img.paste(escuro, (0, 70))
    d.text((60, 250), "v1.0.0", font=BOL(40), fill=(30, 30, 36))
    d.text((60, 306), "Latest", font=MED(20), fill=(40, 140, 60))
    d.text((60, 360), "Assets", font=BOL(26), fill=(30, 30, 36))
    for i, (nome, tam) in enumerate((("Instalar-inFAMOUS.desktop", "1 KB"), ("infamous-ss-deck-v1.0.0.tar.gz", "110 MB"),
                                      ("instalar.sh", "1 KB"))):
        y = 410 + i * 64
        d.rectangle([60, y, 1220, y + 58], outline=(215, 218, 224), fill=(232, 240, 255) if (sel and i == 0) else None)
        d.text((90, y + 15), nome, font=MED(24), fill=(9, 105, 218))
        d.text((1190, y + 15), tam, font=REG(22), fill=(100, 100, 110), anchor="ra")
    return img


def tela_downloads(dlg=False):
    img = tela_vazia()
    janela(img, t("f_down"))
    d = ImageDraw.Draw(img)
    icone_arquivo(d, 120, 160, "Instalar-inFAMOUS.desktop", "▶", destaque=True)
    if dlg:
        d.rounded_rectangle([360, 300, 920, 540], 14, fill=(46, 48, 56), outline=(90, 94, 104), width=2)
        d.text((640, 360), t("dlg"), font=MED(30), fill=BR, anchor="mm")
        d.rounded_rectangle([420, 440, 630, 500], 8, fill=(60, 64, 74))
        d.text((525, 470), t("dlg_no"), font=MED(24), fill=BR, anchor="mm")
        d.rounded_rectangle([650, 440, 860, 500], 8, fill=(61, 174, 233))
        d.text((755, 470), t("dlg_ok"), font=BOL(24), fill=(255, 255, 255), anchor="mm")
    return img


def tela_biblioteca():
    img = Image.open(STEAM / "fundo.png").convert("RGB").resize((1280, 413))
    base = tela_vazia((27, 32, 40))
    base.paste(Image.blend(img, Image.new("RGB", img.size, (27, 32, 40)), 0.25), (0, 0))
    lg = Image.open(STEAM / "logo.png").convert("RGBA")
    lg = lg.resize((560, int(lg.height * 560 / lg.width)))
    base.paste(lg, (60, 200 - lg.height // 2), lg)
    d = ImageDraw.Draw(base)
    d.rounded_rectangle([60, 450, 420, 530], 6, fill=(89, 191, 64))
    d.polygon([(100, 470), (100, 510), (132, 490)], fill=(255, 255, 255))
    d.text((160, 474), t("jogar"), font=BOL(32), fill=(255, 255, 255))
    d.text((60, 580), "inFAMOUS Second Son", font=BOL(34), fill=BR)
    return base


def tela_carregando():
    arte = Image.open(ARTE / "delsin-steamdeck.png").convert("RGB")
    sc = max(1280 / arte.width, 800 / arte.height)
    arte = arte.resize((int(arte.width * sc), int(arte.height * sc)))
    x = int((arte.width - 1280) * 0.35)
    img = arte.crop((x, 0, x + 1280, 800)).convert("RGBA")
    ov = Image.new("RGBA", img.size)
    od = ImageDraw.Draw(ov)
    for j in range(800):
        tt = max(0.0, (j - 360) / 440)
        od.line([(0, j), (1280, j)], fill=(5, 6, 8, int(215 * tt)))
    img.alpha_composite(ov)
    lg = Image.open(ARTE / "logo-vertical.png").convert("RGBA")
    lg = lg.resize((420, int(lg.height * 420 / lg.width)))
    img.alpha_composite(lg, (60, 120))
    d = ImageDraw.Draw(img)
    d.text((64, 640), t("carregando"), font=TIT(40), fill=BR)
    d.rectangle([64, 700, 664, 708], fill=(40, 40, 44))
    d.rectangle([64, 700, 64 + 410, 708], fill=AM)
    return img.convert("RGB")


def tela_inst(nome):
    return Image.open(TELAS / f"{nome}-{L}.png").convert("RGB")


# ---------- quadro: o Deck desenhado, o passo em cima ----------
FUNDO = None


def fundo_geral():
    global FUNDO
    if FUNDO is None:
        a = Image.open(ARTE / "delsin-steamdeck.png").convert("RGB").resize((W, H))
        a = a.filter(ImageFilter.GaussianBlur(30))
        FUNDO = Image.blend(a, Image.new("RGB", (W, H), (8, 9, 11)), 0.82)
    return FUNDO.copy()


SX, SY, SW, SH = 480, 300, 960, 600  # a tela do Deck no quadro


def deck(img):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([170, 250, 1750, 950], 150, fill=(30, 31, 35), outline=(55, 56, 62), width=3)
    d.rounded_rectangle([SX - 18, SY - 18, SX + SW + 18, SY + SH + 18], 18, fill=(10, 10, 12))
    for cx in (300, 1620):  # analogicos
        d.ellipse([cx - 62, 360 - 62, cx + 62, 360 + 62], fill=(20, 20, 23))
        d.ellipse([cx - 42, 360 - 42, cx + 42, 360 + 42], fill=(48, 49, 54))
    d.rectangle([272, 520, 328, 540], fill=(48, 49, 54))
    d.rectangle([290, 502, 310, 558], fill=(48, 49, 54))
    for dx, dy, letra in ((0, -38, "Y"), (-38, 0, "X"), (38, 0, "B"), (0, 38, "A")):
        x, y = 1620 + dx, 530 + dy
        d.ellipse([x - 20, y - 20, x + 20, y + 20], fill=(48, 49, 54))
        d.text((x, y), letra, font=BOL(20), fill=(170, 170, 176), anchor="mm")
    for cx in (300, 1620):  # trackpads
        d.rounded_rectangle([cx - 70, 640, cx + 70, 780], 18, fill=(40, 41, 46))


def quadro(tela, passo=None, titulo="", sub="", toque=None, prog_toque=0.0):
    img = fundo_geral()
    deck(img)
    img.paste(tela.resize((SW, SH), Image.LANCZOS), (SX, SY))
    d = ImageDraw.Draw(img)
    if passo:
        d.text((W // 2, 52), t("passo").format(passo), font=MED(26), fill=AM, anchor="ma")
    if titulo:
        d.text((W // 2, 92), titulo, font=TIT(70), fill=BR, anchor="ma")
    if sub:
        d.text((W // 2, 186), sub, font=REG(32), fill=(205, 203, 196), anchor="ma")
    if toque is not None and prog_toque > 0:
        x = SX + toque[0] * SW / 1280
        y = SY + toque[1] * SH / 800
        r = 22 + 46 * prog_toque
        a = int(255 * (1 - prog_toque))
        ov = Image.new("RGBA", (W, H))
        od = ImageDraw.Draw(ov)
        od.ellipse([x - r, y - r, x + r, y + r], outline=(255, 255, 255, a), width=6)
        od.ellipse([x - 20, y - 20, x + 20, y + 20], fill=(255, 255, 255, min(200, a + 60)))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    return img


# ---------- cenas ----------
def cena(frames, tela, s, n, passo=None, tit="", sub="", toque=None, toque_em=None, tela2=None, troca_em=None):
    """n quadros; toque_em = quadro do toque; tela2 entra no quadro troca_em."""
    for i in range(n):
        atual = tela2 if (tela2 is not None and troca_em is not None and i >= troca_em) else tela
        pt = 0.0
        if toque_em is not None and toque_em <= i < toque_em + 14:
            pt = (i - toque_em + 1) / 14
        frames.append(quadro(atual, passo, tit, sub, toque, pt))


def intro(frames, n):
    lg = Image.open(ARTE / "logo-vertical.png").convert("RGBA")
    lg = lg.resize((560, int(lg.height * 560 / lg.width)))
    for i in range(n):
        img = fundo_geral().convert("RGBA")
        a = min(1.0, i / 18)
        l2 = lg.copy()
        l2.putalpha(l2.getchannel("A").point(lambda v: int(v * a)))
        img.alpha_composite(l2, ((W - lg.width) // 2, 130))
        d = ImageDraw.Draw(img)
        d.text((W // 2, 720), t("intro"), font=TIT(76), fill=BR + (int(255 * a),), anchor="ma")
        d.text((W // 2, 830), t("intro_sub"), font=REG(34), fill=(205, 203, 196, int(255 * a)), anchor="ma")
        frames.append(img.convert("RGB"))


def fim(frames, n):
    lg = Image.open(ARTE / "logo-vertical.png").convert("RGBA")
    lg = lg.resize((520, int(lg.height * 520 / lg.width)))
    for i in range(n):
        img = fundo_geral().convert("RGBA")
        img.alpha_composite(lg, ((W - lg.width) // 2, 110))
        d = ImageDraw.Draw(img)
        d.text((W // 2, 680), "github.com/KewinBR/infamous-second-son-steamdeck", font=MED(40), fill=AM, anchor="ma")
        d.text((W // 2, 760), t("fim_sub"), font=REG(32), fill=(205, 203, 196), anchor="ma")
        frames.append(img.convert("RGB"))


def main():
    f = []
    s = FPS
    intro(f, int(3.5 * s))
    cena(f, tela_arquivos(), s, int(5.5 * s), 1, t("t1"), t("s1"))
    cena(f, tela_energia(False), s, int(4.5 * s), 2, t("t2"), t("s2"), toque=(640, 570), toque_em=int(2.2 * s),
         tela2=tela_energia(True), troca_em=int(2.2 * s))
    cena(f, tela_navegador(False), s, int(5.5 * s), 3, t("t3"), t("s3"), toque=(260, 440), toque_em=int(2.8 * s),
         tela2=tela_navegador(True), troca_em=int(2.8 * s))
    cena(f, tela_downloads(False), s, int(2.5 * s), 4, t("t4"), t("s4"), toque=(220, 230), toque_em=int(1.0 * s))
    cena(f, tela_downloads(True), s, int(2.5 * s), 4, t("t4"), t("s4"), toque=(755, 470), toque_em=int(1.2 * s))
    cena(f, tela_inst("1-inicio"), s, int(3.5 * s), 4, t("t4"), t("s4"), toque=(220, 584), toque_em=int(2.0 * s))
    cena(f, tela_inst("2-jogo"), s, int(5 * s), 5, t("t5"), t("s5"), toque=(900, 626), toque_em=int(3.4 * s))
    cena(f, tela_inst("3-local"), s, int(4 * s), 6, t("t6"), t("s6"), toque=(400, 420), toque_em=int(2.4 * s))
    estados = ["0_0_6_0_02", "1_0_15_0_14", "1_0_46_0_31", "1_0_8_0_6", "2_0_5_0_85", "3_0_5_0_92", "4_0_6_0_97"]
    for e in estados:
        cena(f, tela_inst(f"inst-{e}"), s, int(1.1 * s), 7, t("t7"), t("s7"))
    cena(f, tela_inst("5-pronto"), s, int(3.5 * s), 8, t("t8"), t("s8"), toque=(266, 574), toque_em=int(2.0 * s))
    cena(f, tela_biblioteca(), s, int(3.5 * s), 8, t("t8"), t("s8"), toque=(240, 490), toque_em=int(1.8 * s))
    cena(f, tela_carregando(), s, int(3 * s), 8, t("t8"), t("s8"))
    fim(f, int(4 * s))
    with tempfile.TemporaryDirectory() as tmp:
        for i, q in enumerate(f):
            q.save(f"{tmp}/q{i:05d}.jpg", quality=92)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/q%05d.jpg",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart",
                        str(SAIDA)], check=True)
    print(SAIDA, len(f) / FPS, "s")


if __name__ == "__main__":
    main()
