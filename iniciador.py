"""Iniciador do atalho da Steam: busca uma versao nova do port nas releases do GitHub, atualiza se tiver (tela no
mesmo visual do instalador) e abre o jogo (rodar.sh). Sem internet, com o GitHub fora ou com "atualizar": false no
config.json, abre direto a versao instalada. Saves, cache de shaders e opcoes (user/) nunca sao tocados; a versao
anterior do port fica em port.anterior (o menu do port pode voltar pra ela).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP / "instalador"))
import nucleo  # noqa: E402
from textos import T, idioma_inicial  # noqa: E402

REPO = "KewinBR/infamous-second-son-steamdeck"
API = f"https://api.github.com/repos/{REPO}/releases/latest"


def versao_tupla(v: str):
    return tuple(int(x) for x in v.lstrip("v").split(".") if x.isdigit())


def ultima_release(timeout=4.0):
    req = urllib.request.Request(API, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "infamous-ss-deck"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        rel = json.load(r)
    asset = next((a for a in rel.get("assets", []) if a["name"].startswith("infamous-ss-deck-")
                  and a["name"].endswith(".tar.gz")), None)
    return rel.get("tag_name", ""), asset


def aplicar(pacote: Path, progresso):
    """Troca os arquivos do iniciador e o port pelos do pacote novo (user/ e logs/ ficam)."""
    c = nucleo.ler_config()
    with tempfile.TemporaryDirectory(dir=APP.parent) as tmp:
        with tarfile.open(pacote) as t:
            t.extractall(tmp, filter="data")
        novo = Path(tmp) / "infamous-ss-deck"
        progresso(0.85)
        for item in novo.iterdir():
            if item.name in ("user", "logs", "port.tar.gz"):
                continue
            alvo = APP / item.name
            if alvo.is_dir():
                shutil.rmtree(alvo)
            elif alvo.exists():
                alvo.unlink()
            shutil.move(str(item), alvo)
        port = Path(c["port"])
        anterior = port.with_name("port.anterior")
        shutil.rmtree(anterior, ignore_errors=True)
        temp_port = port.with_name("port.novo")
        shutil.rmtree(temp_port, ignore_errors=True)
        temp_port.mkdir()
        subprocess.run(["tar", "-xzf", str(novo / "port.tar.gz"), "-C", str(temp_port), "--strip-components=1"],
                       check=True)
        if port.exists():
            port.rename(anterior)
        temp_port.rename(port)
    c["versao"] = (APP / "VERSAO").read_text().strip()
    nucleo.gravar_config(c)
    progresso(1.0)


def tela_atualizando(tag: str, url: str, tamanho: int) -> bool:
    import tkinter as tk
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.configure(bg="black")
    cv = tk.Canvas(root, width=1280, height=800, highlightthickness=0, bg="black")
    cv.pack()
    fundo = tk.PhotoImage(file=str(APP / "instalador" / "assets" / "fundo-instalando.png"))
    logo = tk.PhotoImage(file=str(APP / "instalador" / "assets" / "logo-horizontal-360.png"))
    cv.create_image(0, 0, image=fundo, anchor="nw")
    cv.create_image(56, 60, image=logo, anchor="nw")
    cv.create_text(56, 300, text=T("atualizando"), font=("ISS Deck Stencil", -64), fill="#EBE9E2", anchor="nw")
    cv.create_rectangle(56, 386, 136, 391, fill="#F2B71E", width=0)
    cv.create_text(56, 420, text=T("atualizando_texto").format(tag), font=("Barlow", -22), fill="#cdcbc4",
                   anchor="nw", width=700)
    cv.create_rectangle(56, 500, 816, 512, fill="#28282c", width=0)
    barra = cv.create_rectangle(56, 500, 56, 512, fill="#F2B71E", width=0)
    estado = {"f": 0.0, "fim": False, "ok": False}

    def progresso(f):
        estado["f"] = f

    def trabalho():
        try:
            with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as arq:
                caminho = Path(arq.name)
                with urllib.request.urlopen(url, timeout=20) as r:
                    lido = 0
                    while bloco := r.read(1 << 20):
                        arq.write(bloco)
                        lido += len(bloco)
                        progresso(0.8 * lido / max(1, tamanho))
            aplicar(caminho, progresso)
            caminho.unlink(missing_ok=True)
            estado["ok"] = True
        except Exception as e:  # sem atualizar, o jogo abre na versao instalada
            print("atualizacao falhou:", e, file=sys.stderr)
        estado["fim"] = True

    def tique():
        cv.coords(barra, 56, 500, 56 + int(760 * estado["f"]), 512)
        if estado["fim"]:
            root.destroy()
        else:
            root.after(100, tique)

    threading.Thread(target=trabalho, daemon=True).start()
    tique()
    root.mainloop()
    return estado["ok"]


def main():
    T.lang = idioma_inicial()
    c = nucleo.ler_config()
    if c.get("atualizar", True) and os.environ.get("ISS_SEM_ATUALIZAR") != "1":
        try:
            tag, asset = ultima_release()
            if asset and versao_tupla(tag) > versao_tupla(c.get("versao", "0")):
                tela_atualizando(tag, asset["browser_download_url"], asset.get("size", 0))
        except Exception as e:  # sem internet: segue
            print("sem verificar atualizacao:", e, file=sys.stderr)
    os.execvp("bash", ["bash", str(APP / "rodar.sh")])


if __name__ == "__main__":
    main()
