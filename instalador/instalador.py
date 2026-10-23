"""Instalador do inFAMOUS Second Son - Steamdeck Version (Tk, tela cheia 1280x800, toque e controle).

    python3 instalador.py            # no Deck (Modo Desktop)
    DEMO=1 python3 instalador.py     # sem instalar nada: pacotes e progresso de mentira (previas)
    DEMO=1 PRINTS=pasta python3 instalador.py   # passa por todas as telas e salva um print de cada (PC, Pillow)

Controle no Modo Desktop do Deck: direcional ou analogico = setas, A = Enter, B = Esc. Toque tambem funciona.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path

import nucleo
from textos import T, idioma_inicial

AQUI = Path(__file__).resolve().parent
ASSETS = AQUI / "assets"
FONTES = AQUI / "fontes"
DEMO = os.environ.get("DEMO") == "1"
W, H = 1280, 800
AM = "#F2B71E"
BR = "#EBE9E2"
CI = "#969696"
ESC = "#0C0C0E"
TIT = "ISS Deck Stencil"


def registrar_fontes():
    """As fontes OFL do instalador (estencil e Barlow): no Linux pelo fontconfig do usuario, no Windows so pro
    processo (previas)."""
    if sys.platform == "win32":
        import ctypes
        try:  # pixels de verdade (sem a escala do Windows), como no Deck
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass
        for f in FONTES.glob("*.ttf"):
            ctypes.windll.gdi32.AddFontResourceExW(str(f), 0x10, 0)
        return
    destino = Path.home() / ".local" / "share" / "fonts" / nucleo.APP
    if not (destino / "ISSDeckStencil.ttf").exists():
        destino.mkdir(parents=True, exist_ok=True)
        for f in FONTES.glob("*.ttf"):
            shutil.copy(f, destino / f.name)
        subprocess.run(["fc-cache", "-f", str(destino)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def gb(n: int) -> str:
    return f"{n / 1024 ** 3:.1f}".replace(".", "," if T.lang == "pt" else ".") + " GB"


class App:
    def __init__(self):
        registrar_fontes()
        self.root = tk.Tk()
        self.root.title("inFAMOUS Second Son - Steamdeck Version")
        self.root.configure(bg="black")
        if sys.platform == "win32" or os.environ.get("JANELA") == "1":
            self.root.geometry(f"{W}x{H}+0+0")
            self.root.resizable(False, False)
        else:
            self.root.attributes("-fullscreen", True)
        self.cv = tk.Canvas(self.root, width=W, height=H, highlightthickness=0, bg="black")
        self.cv.pack()
        self.img = {p.stem: tk.PhotoImage(file=str(p)) for p in ASSETS.glob("*.png")}
        # Tamanhos em pixels (negativos no Tk), os mesmos da previa aprovada (1280x800).
        familia = {"tit": (TIT,), "reg": ("Barlow",), "med": ("Barlow Medium",), "bol": ("Barlow", "bold")}
        self.f = {}
        for nome in ("tit64", "tit34", "tit30", "reg22", "reg20", "reg19", "reg16", "med25", "med22", "med20",
                     "med17", "med15", "bol26", "bol25", "bol17"):
            fam = familia[nome[:3]]
            self.f[nome] = (fam[0], -int(nome[3:])) + fam[1:]
        self.focaveis: list[dict] = []
        self.foco = 0
        self.pacotes: list[nucleo.Pacote] = []
        self.pasta_jogo: Path | None = None
        self.lugares: list[nucleo.Local] = []
        self.destino: nucleo.Local | None = None
        self.prog = nucleo.Progresso()
        self.inst: nucleo.Instalacao | None = None
        self.tela = ""
        for k in ("<Up>", "<Down>", "<Left>", "<Right>", "<Tab>", "<Shift-Tab>"):
            self.root.bind(k, self.mover)
        for k in ("<Return>", "<KP_Enter>", "<space>"):
            self.root.bind(k, lambda e: self.ativar())
        for k in ("<Escape>", "<BackSpace>"):
            self.root.bind(k, lambda e: self.voltar())
        self.mostrar("inicio")

    # ---------- desenho ----------
    def limpar(self, fundo: str):
        self.cv.delete("all")
        self.focaveis = []
        self.foco = 0
        self.cv.create_image(0, 0, image=self.img[fundo], anchor="nw")

    def texto(self, x, y, s, fonte, cor=BR, largura=0, anchor="nw", tag=None):
        return self.cv.create_text(x, y, text=s, font=self.f[fonte], fill=cor, anchor=anchor, width=largura or 0,
                                   tags=tag)

    def cabeca(self, passo: int, titulo: str):
        self.cv.create_image(56, 40, image=self.img["logo-horizontal"], anchor="nw")
        x = W - 56
        for i in range(4, 0, -1):
            n = T(f"passo{i}")
            cor = AM if i == passo else (BR if i < passo else "#6e6e6e")
            t = self.texto(x, 52, n, "med17", cor, anchor="ne")
            x1, y1, x2, y2 = self.cv.bbox(t)
            if i == passo:
                self.cv.create_rectangle(x1, 76, x2, 79, fill=AM, width=0)
            x = x1 - 34
        self.texto(56, 206, titulo, "tit64")
        self.cv.create_rectangle(56, 292, 136, 297, fill=AM, width=0)

    def rodape(self, itens: list[tuple[str, str]]):
        self.cv.create_rectangle(0, H - 64, W, H, fill="#08090b", width=0)
        x = W - 56
        for botao, chave in reversed(itens):
            t = self.texto(x, H - 32, T(chave), "med20", anchor="e")
            x = self.cv.bbox(t)[0] - 10
            self.cv.create_oval(x - 30, H - 47, x, H - 17, fill="#1e1f23", outline="#c8c8c8", width=2)
            self.texto(x - 15, H - 32, botao, "bol17", anchor="center")
            x -= 64

    def creditos(self):
        y = H - 64 - 58
        self.texto(56, y, T("creditos_por"), "med15", CI)
        t = self.texto(56, y + 16, "Kewin Lima", "tit30", AM)
        self.texto(self.cv.bbox(t)[2] + 14, y + 27, T("creditos_base"), "reg16", CI)

    def focavel(self, desenhar, acao, foco_inicial=False):
        """desenhar(sel) devolve os ids desenhados; acao() roda com A/toque."""
        item = {"desenhar": desenhar, "acao": acao, "ids": []}
        self.focaveis.append(item)
        if foco_inicial:
            self.foco = len(self.focaveis) - 1
        return item

    def redesenhar_foco(self):
        for i, it in enumerate(self.focaveis):
            for d in it["ids"]:
                self.cv.delete(d)
            it["ids"] = it["desenhar"](i == self.foco)
            for d in it["ids"]:
                self.cv.tag_bind(d, "<Button-1>", lambda e, n=i: self.tocar(n))

    def tocar(self, n):
        self.foco = n
        self.redesenhar_foco()
        self.ativar()

    def mover(self, e):
        if not self.focaveis:
            return
        passo = -1 if e.keysym in ("Up", "Left") or e.state & 1 else 1
        self.foco = (self.foco + passo) % len(self.focaveis)
        self.redesenhar_foco()

    def ativar(self):
        if self.focaveis:
            self.focaveis[self.foco]["acao"]()

    def voltar(self):
        anterior = {"inicio": None, "jogo": "inicio", "local": "jogo", "pronto": None, "erro": "inicio"}
        if self.tela == "instalando":
            if self.inst:
                self.inst.cancelado = True
            return
        destino = anterior.get(self.tela)
        if destino:
            self.mostrar(destino)
        elif self.tela in ("inicio", "pronto"):
            self.root.destroy()

    # ---------- componentes ----------
    def botao(self, x, y, w, chave, acao, primario=True, foco_inicial=False):
        def desenhar(sel):
            ids = []
            if primario:
                ids.append(self.cv.create_rectangle(x, y, x + w, y + 64, fill=AM, width=0))
            else:
                ids.append(self.cv.create_rectangle(x, y, x + w, y + 64, outline=BR, width=2))
            if sel:
                ids.append(self.cv.create_rectangle(x - 5, y - 5, x + w + 5, y + 69, outline=BR, width=3))
            ids.append(self.texto(x + w / 2, y + 33, T(chave), "tit34", ESC if primario else BR, anchor="center"))
            return ids
        return self.focavel(desenhar, acao, foco_inicial)

    def cartao(self, x, y, w, h, titulo, sub, acao, check=None, direita="", foco_inicial=False):
        def desenhar(sel):
            ids = [self.cv.create_image(x, y, image=self.img[f"card-{w}x{h}{'-sel' if sel else ''}"], anchor="nw")]
            tx = x + 30
            c = check() if callable(check) else check
            if c is not None:
                cy = y + h // 2
                ids.append(self.cv.create_rectangle(x + 26, cy - 13, x + 52, cy + 13, outline=AM if c else CI,
                                                    width=3))
                if c:
                    ids.append(self.cv.create_line(x + 31, cy, x + 37, cy + 7, x + 48, cy - 8, fill=AM, width=4))
                tx = x + 72
            ids.append(self.texto(tx, y + 18, titulo, "bol26", BR))
            ids.append(self.texto(tx, y + 54, sub, "reg19", CI))
            if direita:
                ids.append(self.texto(x + w - 30, y + h // 2, direita, "med22", AM if sel else BR, anchor="e"))
            return ids
        return self.focavel(desenhar, acao, foco_inicial)

    # ---------- telas ----------
    def mostrar(self, tela: str):
        self.tela = tela
        getattr(self, f"tela_{tela}")()
        self.redesenhar_foco()

    def tela_inicio(self):
        self.limpar("fundo-inicio")
        lg = self.img["logo-vertical"]
        self.cv.create_image(64, 70, image=lg, anchor="nw")
        y = 70 + lg.height() + 26
        t = self.texto(70, y, T("inicio_texto"), "reg22", "#cdcbc4", largura=560)
        y = self.cv.bbox(t)[3] + 26
        self.botao(70, y, 300, "instalar", lambda: self.mostrar("jogo"), foco_inicial=True)
        self.botao(390, y, 170, "outro_idioma", self.trocar_idioma, primario=False)
        self.creditos()
        self.rodape([("A", "selecionar"), ("B", "sair")])

    def trocar_idioma(self):
        T.lang = "en" if T.lang == "pt" else "pt"
        self.mostrar(self.tela)
        self.foco = 1
        self.redesenhar_foco()

    def tela_jogo(self):
        self.limpar("fundo-passos")
        self.cabeca(1, T("jogo_titulo"))
        if not self.pacotes and not DEMO:
            self.pacotes = nucleo.procurar_pkgs()
        if DEMO and not self.pacotes:
            self.pacotes = [nucleo.Pacote(Path("/run/media/deck/SD/ps4/Infamous Second son.pkg"), 25877323776,
                                          "CUSA00004", "base"),
                            nucleo.Pacote(Path("/run/media/deck/SD/ps4/inFAMOUS Second Son-up.pkg"), 3953328128,
                                          "CUSA00004", "update")]
        ordem = sorted(self.pacotes, key=lambda p: (p.tipo != "base", -p.tamanho))[:2]
        y = 370
        if ordem:
            self.texto(56, 318, T("jogo_achei"), "reg22", "#cdcbc4", largura=900)
        else:
            self.texto(56, 318, T("jogo_nada"), "reg22", "#cdcbc4", largura=900)
        for p in ordem:
            sub = f"{T('tipo_' + p.tipo)}   •   {gb(p.tamanho)}   •   {p.local}"
            def alternar(p=p):
                p.marcado = not p.marcado
                self.redesenhar_foco()
            self.cartao(56, y, 700, 92, p.caminho.name, sub, alternar, check=lambda p=p: p.marcado,
                        foco_inicial=y == 370)
            y += 104
        self.cartao(56, y, 340, 92, T("procurar"), T("procurar_sub"), self.procurar_pasta, direita="›")
        self.cartao(416, y, 340, 92, T("ja_extraido"), T("ja_extraido_sub"), self.escolher_extraido, direita="›")
        self.botao(800, y + 14, 200, "continuar", self.continuar_jogo)
        self.rodape([("A", "marcar"), ("B", "voltar")])

    def procurar_pasta(self):
        pasta = self.escolher_pasta(T("procurar"))
        if pasta:
            self.pacotes = nucleo.procurar_pkgs([Path(pasta)], profundidade=3) + self.pacotes
            self.mostrar("jogo")

    def escolher_extraido(self):
        pasta = self.escolher_pasta(T("ja_extraido"))
        if pasta and (Path(pasta) / "eboot.bin").exists():
            self.pasta_jogo = Path(pasta)
            self.mostrar("local")

    def escolher_pasta(self, titulo):
        """Seletor de pasta do sistema (KDE/GTK), grande e por toque; sem eles, o do Tk."""
        for cmd in (["kdialog", "--getexistingdirectory", str(Path.home()), "--title", titulo],
                    ["zenity", "--file-selection", "--directory", f"--title={titulo}"]):
            if shutil.which(cmd[0]):
                r = subprocess.run(cmd, capture_output=True, text=True)
                return r.stdout.strip() or None
        from tkinter import filedialog
        return filedialog.askdirectory(title=titulo) or None

    def continuar_jogo(self):
        marcados = [p for p in self.pacotes if p.marcado]
        if not any(p.tipo == "base" for p in marcados):
            return
        self.pasta_jogo = None
        self.mostrar("local")

    def tela_local(self):
        self.limpar("fundo-passos")
        self.cabeca(2, T("local_titulo"))
        self.texto(56, 318, T("local_texto"), "reg22", "#cdcbc4", largura=900)
        if not self.lugares:
            self.lugares = nucleo.locais() if not DEMO else [
                nucleo.Local("ssd", Path.home(), 212 * 1024 ** 3, False),
                nucleo.Local("SD", Path("/run/media/deck/SD"), 87 * 1024 ** 3, True)]
        y = 370
        for i, l in enumerate(self.lugares[:3]):
            nome = T("sd") if l.sd else T("ssd")
            sub = f"{T('sd_sub') if l.sd else T('ssd_sub')}   •   {gb(l.livre)} {T('livres')}"
            cabe = l.livre >= nucleo.ESPACO_JOGO or self.pasta_jogo
            def escolher(l=l, cabe=cabe):
                if cabe:
                    self.destino = l
                    self.iniciar_instalacao()
            self.cartao(56, y, 700, 100, nome, sub if cabe else T("sem_espaco"), escolher,
                        direita=T("recomendado") if i == 0 else "", foco_inicial=i == 0)
            y += 114
        self.rodape([("A", "selecionar"), ("B", "voltar")])

    def iniciar_instalacao(self):
        self.prog = nucleo.Progresso()
        self.t0 = time.time()
        if not DEMO:
            base = next((p for p in self.pacotes if p.marcado and p.tipo == "base"), None)
            upd = next((p for p in self.pacotes if p.marcado and p.tipo == "update"), None)
            pacote_port = AQUI.parent / "port.tar.gz"
            self.inst = nucleo.Instalacao(base, upd, self.pasta_jogo, self.destino, pacote_port, self.prog,
                                          criar_atalho=atalho_steam)
            self.inst.start()
        self.mostrar("instalando")
        self.atualizar_progresso()

    def tela_instalando(self):
        self.limpar("fundo-instalando")
        self.cabeca(3, T("instalando_titulo"))
        self.etapas_ids = []
        self.rodape([("B", "cancelar")])

    def atualizar_progresso(self):
        if self.tela != "instalando":
            return
        p = self.prog
        if DEMO:  # 31% na etapa 1, como na previa aprovada
            p.etapa, p.fracao, p.total = 1, 0.46, 0.31
        for d in self.etapas_ids:
            self.cv.delete(d)
        ids = []
        nomes = [T("etapa_port"), T("etapa_base"), T("etapa_update"), T("etapa_preparar"), T("etapa_atalho")]
        y = 330
        for i, nome in enumerate(nomes):
            feito = i < p.etapa or p.pronto
            atual = i == p.etapa and not p.pronto
            if feito:
                ids.append(self.cv.create_line(62, y + 14, 70, y + 22, 84, y + 4, fill=AM, width=4))
            elif atual:
                a = (time.time() * 360) % 360
                ids.append(self.cv.create_arc(58, y, 86, y + 28, start=a, extent=270, style="arc", outline=AM,
                                              width=4))
            else:
                ids.append(self.cv.create_oval(66, y + 8, 78, y + 20, outline="#6e6e6e", width=2))
            ids.append(self.texto(104, y, nome, "med25", BR if (feito or atual) else "#787878"))
            if atual and p.fracao > 0:
                ids.append(self.texto(760, y, f"{int(p.fracao * 100)}%", "bol25", AM, anchor="ne"))
            y += 52
        ids.append(self.cv.create_rectangle(56, 620, 816, 632, fill="#28282c", width=0))
        ids.append(self.cv.create_rectangle(56, 620, 56 + int(760 * p.total), 632, fill=AM, width=0))
        info = f"{T('total')}: {int(p.total * 100)}%"
        dec = time.time() - getattr(self, "t0", time.time())
        if DEMO:
            info += f"   •   {T('restam').format(18)}"
        elif p.total > 0.03 and dec > 20:
            info += f"   •   {T('restam').format(max(1, round(dec / p.total * (1 - p.total) / 60)))}"
        info += f"   •   {T('tomada')}"
        ids.append(self.texto(56, 646, info, "reg20", CI))
        self.etapas_ids = ids
        if p.erro:
            self.erro = p.erro
            self.mostrar("erro")
            return
        if p.pronto:
            self.mostrar("pronto")
            return
        self.root.after(120, self.atualizar_progresso)

    def tela_pronto(self):
        self.limpar("fundo-pronto")
        self.cabeca(4, T("pronto_titulo"))
        t = self.texto(56, 318, T("pronto_texto"), "reg22", "#cdcbc4", largura=540)
        y = self.cv.bbox(t)[3] + 16
        t = self.texto(56, y, T("pronto_menu"), "med22", AM, largura=540)
        y = self.cv.bbox(t)[3] + 30
        self.botao(56, y, 420, "modo_jogo", modo_de_jogo, foco_inicial=True)
        self.creditos()
        self.rodape([("A", "selecionar"), ("B", "sair")])

    def tela_erro(self):
        self.limpar("fundo-passos")
        self.cabeca(3, T("erro_titulo"))
        self.texto(56, 318, T("erro_texto"), "reg22", "#cdcbc4", largura=800)
        self.texto(56, 420, getattr(self, "erro", ""), "reg19", CI, largura=900)
        self.botao(56, 560, 300, "tentar_de_novo", lambda: self.mostrar("local"), foco_inicial=True)
        self.rodape([("A", "selecionar"), ("B", "voltar")])


def atalho_steam(raiz: Path, port: Path):
    import steam
    steam.criar_atalho(raiz, port)


def modo_de_jogo():
    """Volta ao Modo de Jogo do Deck (o atalho aparece na biblioteca)."""
    if shutil.which("steamos-session-select"):
        subprocess.Popen(["steamos-session-select", "gamescope"])
    else:
        sys.exit(0)


def prints(app: App, pasta: Path):
    """Passa por todas as telas e salva um print de cada (previas no PC; precisa do Pillow)."""
    from PIL import ImageGrab
    pasta.mkdir(parents=True, exist_ok=True)
    app.root.attributes("-topmost", True)
    app.root.lift()
    seq = ["inicio", "jogo", "local", "instalando", "pronto", "erro"]

    def tirar(i=0):
        if i:
            app.root.update()
            x, y = app.cv.winfo_rootx(), app.cv.winfo_rooty()
            ImageGrab.grab((x, y, x + W, y + H)).save(pasta / f"{i}-{seq[i - 1]}-{T.lang}.png")
        if i == len(seq):
            app.root.destroy()
            return
        if seq[i] == "instalando":
            app.prog = nucleo.Progresso()
            app.mostrar("instalando")
            app.atualizar_progresso()
        else:
            app.erro = "pkgx falhou (1): sem espaço no destino" if T.lang == "pt" else "pkgx failed (1): no space left"
            app.mostrar(seq[i])
        app.root.after(900, lambda: tirar(i + 1))
    app.root.after(1200, tirar)


if __name__ == "__main__":
    if not DEMO:  # registro pra issues (~/.config/infamous-ss-deck/instalador.log)
        nucleo.CONFIG.parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = sys.stderr = open(nucleo.CONFIG.parent / "instalador.log", "a", buffering=1, encoding="utf-8")
        print(time.strftime("== %Y-%m-%d %H:%M:%S"), "instalador", (nucleo.PACOTE / "VERSAO").read_text().strip()
              if (nucleo.PACOTE / "VERSAO").exists() else "")
    T.lang = os.environ.get("IDIOMA") or idioma_inicial()
    app = App()
    if os.environ.get("PRINTS"):
        prints(app, Path(os.environ["PRINTS"]))
    app.root.mainloop()
