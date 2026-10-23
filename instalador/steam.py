"""Atalho do jogo na biblioteca da Steam (jogo fora da Steam), com as artes do Steamdeck Version.

A Steam reescreve o shortcuts.vdf enquanto esta aberta: fecha a Steam (steam -shutdown), grava o atalho e as artes
(config/grid) e faz copia de seguranca do arquivo antes. No Modo de Jogo a sessao reabre a Steam sozinha; no Modo
Desktop ela volta ao abrir de novo (o botao "Voltar ao Modo de Jogo" do instalador ja faz isso).
Mesmo nome = atualiza a entrada (mantem o appid, o tempo de jogo e a configuracao de controle).
"""
from __future__ import annotations

import binascii
import os
import shutil
import struct
import subprocess
import time
from pathlib import Path

NOME = os.environ.get("ISS_NOME_ATALHO", "inFAMOUS Second Son")
STEAM = Path.home() / ".local" / "share" / "Steam"
ARTES = Path(__file__).resolve().parent / "assets" / "steam"


def ler_vdf(dados: bytes, i: int = 0):
    obj = {}
    while True:
        tipo = dados[i]
        i += 1
        if tipo == 0x08:
            return obj, i
        fim = dados.index(b"\0", i)
        chave = dados[i:fim].decode("utf-8", "replace")
        i = fim + 1
        if tipo == 0x00:
            obj[chave], i = ler_vdf(dados, i)
        elif tipo == 0x01:
            fim = dados.index(b"\0", i)
            obj[chave] = dados[i:fim].decode("utf-8", "replace")
            i = fim + 1
        elif tipo == 0x02:
            obj[chave] = struct.unpack_from("<i", dados, i)[0]
            i += 4
        else:
            raise ValueError(f"tipo VDF desconhecido 0x{tipo:02x} em {i}")


def escrever_vdf(obj: dict) -> bytes:
    saida = bytearray()
    for chave, valor in obj.items():
        nome = chave.encode("utf-8") + b"\0"
        if isinstance(valor, dict):
            saida += b"\x00" + nome + escrever_vdf(valor)
        elif isinstance(valor, int):
            saida += b"\x02" + nome + struct.pack("<i", valor)
        else:
            saida += b"\x01" + nome + str(valor).encode("utf-8") + b"\0"
    return bytes(saida + b"\x08")


def steam_aberta() -> bool:
    return subprocess.run(["pgrep", "-x", "steam"], capture_output=True).returncode == 0


def fechar_steam(limite: float = 90) -> bool:
    if not steam_aberta():
        return True
    subprocess.run(["steam", "-shutdown"], capture_output=True)
    fim = time.time() + limite
    while time.time() < fim:
        if not steam_aberta():
            return True
        time.sleep(0.2)
    return False


def gravar_atalho(config: Path, exe: Path, pasta: Path):
    vdf = config / "shortcuts.vdf"
    dados = vdf.read_bytes() if vdf.exists() else b"\x00shortcuts\x00\x08\x08"
    raiz, _ = ler_vdf(dados)
    atalhos = raiz.setdefault("shortcuts", {})
    exe_q = f'"{exe}"'
    appid = (binascii.crc32((exe_q + NOME).encode("utf-8")) | 0x80000000) & 0xFFFFFFFF
    assinado = struct.unpack("<i", struct.pack("<I", appid))[0]
    entrada = {
        "appid": assinado, "AppName": NOME, "Exe": exe_q, "StartDir": f'"{pasta}"', "icon": "",
        "ShortcutPath": "", "LaunchOptions": "", "IsHidden": 0, "AllowDesktopConfig": 1, "AllowOverlay": 1,
        "OpenVR": 0, "Devkit": 0, "DevkitGameID": "", "DevkitOverrideAppID": 0, "LastPlayTime": 0,
        "FlatpakAppID": "", "tags": {},
    }
    chave = next((k for k, v in atalhos.items() if v.get("AppName") == NOME), None)
    if chave is None:
        chave = str(max((int(k) for k in atalhos), default=-1) + 1)
    else:
        antigo = atalhos[chave]
        if antigo.get("appid"):
            assinado = antigo["appid"]
            appid = struct.unpack("<I", struct.pack("<i", assinado))[0]
            entrada["appid"] = assinado
        for campo in ("LastPlayTime", "tags", "LaunchOptions"):
            if campo in antigo:
                entrada[campo] = antigo[campo]
    grid = config / "grid"
    grid.mkdir(parents=True, exist_ok=True)
    for arquivo, sufixo in (("capa.png", "p"), ("horizontal.png", ""), ("fundo.png", "_hero"), ("logo.png", "_logo"),
                            ("icone.png", "_icon")):
        if (ARTES / arquivo).exists():
            shutil.copyfile(ARTES / arquivo, grid / f"{appid}{sufixo}.png")
    entrada["icon"] = str(grid / f"{appid}_icon.png")
    if vdf.exists():
        shutil.copyfile(vdf, vdf.with_name(vdf.name + time.strftime(".bak-%Y%m%d-%H%M%S")))
    atalhos[chave] = entrada
    novo = escrever_vdf(raiz)
    ler_vdf(novo)  # le de volta antes de trocar
    tmp = vdf.with_suffix(".vdf.tmp")
    tmp.write_bytes(novo)
    os.replace(tmp, vdf)
    return appid


def criar_atalho(raiz: Path, port: Path):
    """Um atalho por usuario da Steam no Deck, apontando pro iniciador instalado."""
    exe = Path.home() / ".local" / "share" / "infamous-ss-deck" / "iniciar.sh"
    configs = sorted((STEAM / "userdata").glob("*/config"))
    if not configs:
        raise RuntimeError("Steam nao encontrada (~/.local/share/Steam/userdata)")
    if not fechar_steam():
        raise RuntimeError("a Steam nao fechou em 90 s; nada foi mudado")
    for config in configs:
        gravar_atalho(config, exe, exe.parent)
