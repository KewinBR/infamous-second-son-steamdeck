"""Parte sem tela do instalador: acha os .pkg do jogo, classifica (jogo base ou atualizacao), mede o espaco, extrai
com o pkgx, instala o port e cria o atalho na Steam. Nada do jogo sai do Deck nem e baixado.

Layout instalado (DESTINO = ~/ no SSD ou a raiz do cartao SD):
    DESTINO/infamous-ss-deck/jogo/       jogo extraido (base 1.00 + atualizacao 1.07 por cima)
    DESTINO/infamous-ss-deck/port/       o port (pacote da release)
    ~/.config/infamous-ss-deck/config.json
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path

APP = "infamous-ss-deck"
TITULOS = ("CUSA00004", "CUSA00223")  # Europa e EUA: o eboot 1.07 e o mesmo (ponto de entrada 0x61dfd0)
CONFIG = Path.home() / ".config" / APP / "config.json"
AQUI = Path(__file__).resolve().parent
PACOTE = AQUI.parent  # a raiz do pacote da release (VERSAO, rodar.sh, deck/, bin/pkgx, port.tar.gz)
PKGX = Path(os.environ.get("ISS_PKGX", PACOTE / "bin" / "pkgx"))
APPDIR = Path.home() / ".local" / "share" / APP  # iniciador, scripts, user/ (saves, shaders) e logs
ESPACO_JOGO = 32 * 1024 ** 3  # jogo extraido com a atualizacao (~31 GB) e folga


@dataclass
class Pacote:
    caminho: Path
    tamanho: int
    titulo: str = ""
    tipo: str = ""  # "base" ou "update"
    marcado: bool = True

    @property
    def local(self) -> str:
        p = self.caminho.parent.as_posix()
        return p.replace(Path.home().as_posix(), "~")


@dataclass
class Local:
    nome: str
    raiz: Path
    livre: int
    sd: bool


@dataclass
class Progresso:
    etapa: int = 0
    fracao: float = 0.0  # da etapa atual
    total: float = 0.0
    texto: str = ""
    erro: str = ""
    pronto: bool = False
    restante_s: float = -1
    _trava: threading.Lock = field(default_factory=threading.Lock)


def lugares_de_busca() -> list[Path]:
    home = Path.home()
    lugares = [home / "Downloads", home / "Desktop", home]
    media = Path("/run/media")
    if media.is_dir():
        for usuario in media.iterdir():
            if usuario.is_dir():
                lugares += [p for p in usuario.iterdir() if p.is_dir()]
    return [p for p in lugares if p.is_dir()]


def procurar_pkgs(lugares: list[Path] | None = None, profundidade: int = 4) -> list[Pacote]:
    """Os .pkg de mais de 1 GB nas pastas de costume (sem entrar em pastas ocultas nem no proprio port)."""
    achados: dict[Path, Pacote] = {}
    for raiz in lugares or lugares_de_busca():
        base = len(raiz.parts)
        for pasta, subpastas, arquivos in os.walk(raiz, onerror=lambda e: None):
            if len(Path(pasta).parts) - base >= profundidade:
                subpastas[:] = []
            subpastas[:] = [s for s in subpastas if not s.startswith(".") and s != APP]
            for a in arquivos:
                if a.lower().endswith(".pkg"):
                    p = Path(pasta) / a
                    try:
                        t = p.stat().st_size
                    except OSError:
                        continue
                    if t > 1024 ** 3:
                        achados[p.resolve()] = Pacote(p, t)
    pacotes = list(achados.values())
    for p in pacotes:
        classificar(p)
    return [p for p in pacotes if p.titulo in TITULOS]


def classificar(p: Pacote) -> None:
    """Le o cabecalho: content id (titulo) e o tipo pelo pkgx (GD = jogo, GP = atualizacao)."""
    try:
        with open(p.caminho, "rb") as f:
            cab = f.read(0x80)
        if cab[:4] != b"\x7fCNT":
            return
        cid = cab[0x40:0x64].decode("ascii", "replace")
        m = re.search(r"CUSA\d{5}", cid)
        p.titulo = m.group(0) if m else ""
    except OSError:
        return
    flags = ""
    if PKGX.exists():
        try:
            proc = subprocess.Popen([str(PKGX), "-l", str(p.caminho), "/tmp/pkgx-l"], stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, text=True)
            for linha in proc.stdout:
                if "flags:" in linha:
                    flags = linha
                    break
            proc.kill()
        except OSError:
            pass
    if "GP" in flags:
        p.tipo = "update"
    elif "GD" in flags:
        p.tipo = "base"
    else:  # sem pkgx: pelo tamanho (o jogo tem 24 GB, a atualizacao 3,9 GB)
        p.tipo = "base" if p.tamanho > 10 * 1024 ** 3 else "update"


def locais() -> list[Local]:
    res = [Local("ssd", Path.home(), shutil.disk_usage(Path.home()).free, False)]
    media = Path("/run/media")
    if media.is_dir():
        for usuario in media.iterdir():
            if not usuario.is_dir():
                continue
            for m in usuario.iterdir():
                try:
                    if m.is_dir() and os.access(m, os.W_OK):
                        res.append(Local(m.name, m, shutil.disk_usage(m).free, True))
                except OSError:
                    pass
    return res


def ler_config() -> dict:
    try:
        return json.loads(CONFIG.read_text())
    except (OSError, ValueError):
        return {}


def gravar_config(c: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(c, indent=2, ensure_ascii=False))


def instalar_app() -> None:
    """Copia o iniciador, os scripts, as artes e o instalador (usado nas atualizacoes) pro APPDIR. user/ e logs/
    (saves, cache de shaders, opcoes) ficam como estao."""
    APPDIR.mkdir(parents=True, exist_ok=True)
    for item in PACOTE.iterdir():
        if item.name in ("port.tar.gz", "user", "logs"):
            continue
        alvo = APPDIR / item.name
        if alvo.resolve() == item.resolve():
            continue
        if alvo.is_dir():
            shutil.rmtree(alvo)
        elif alvo.exists():
            alvo.unlink()
        if item.is_dir():
            shutil.copytree(item, alvo)
        else:
            shutil.copy2(item, alvo)
    for sh in ("iniciar.sh", "rodar.sh", "bin/pkgx"):
        if (APPDIR / sh).exists():
            (APPDIR / sh).chmod(0o755)


class Instalacao(threading.Thread):
    """Etapas: 0 port, 1 jogo base, 2 atualizacao, 3 preparar (fontes do menu, opcoes), 4 atalho na Steam."""

    PESOS = [0.03, 0.72, 0.15, 0.05, 0.05]

    def __init__(self, base: Pacote | None, update: Pacote | None, pasta_jogo: Path | None, destino: Local,
                 port_pacote: Path, progresso: Progresso, criar_atalho):
        super().__init__(daemon=True)
        self.base, self.update, self.pasta_jogo = base, update, pasta_jogo
        self.raiz = destino.raiz / APP
        self.port_pacote = port_pacote
        self.p = progresso
        self.criar_atalho = criar_atalho
        self.cancelado = False

    def _avanca(self, etapa: int, fracao: float, texto: str = ""):
        with self.p._trava:
            self.p.etapa, self.p.fracao = etapa, max(0.0, min(1.0, fracao))
            self.p.total = sum(self.PESOS[:etapa]) + self.PESOS[etapa] * self.p.fracao
            if texto:
                self.p.texto = texto

    def _pkgx(self, etapa: int, pkg: Pacote, destino: Path):
        destino.mkdir(parents=True, exist_ok=True)
        proc = subprocess.Popen([str(PKGX), str(pkg.caminho), str(destino)], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        padrao = re.compile(r"([\d.]+)/([\d.]+) GiB")
        for linha in proc.stderr:
            if self.cancelado:
                proc.kill()
                raise RuntimeError("cancelado")
            m = padrao.search(linha)
            if m and float(m.group(2)) > 0:
                self._avanca(etapa, float(m.group(1)) / float(m.group(2)))
        saida = proc.stdout.read()
        if proc.wait() != 0:
            raise RuntimeError(f"pkgx falhou ({proc.returncode}): {saida[-400:]}")

    def run(self):
        try:
            self.raiz.mkdir(parents=True, exist_ok=True)
            # 0. o port: o pacote da release ja baixado pelo instalar.sh
            self._avanca(0, 0.1)
            port = self.raiz / "port"
            novo = self.raiz / "port.novo"
            shutil.rmtree(novo, ignore_errors=True)
            novo.mkdir()
            subprocess.run(["tar", "-xzf", str(self.port_pacote), "-C", str(novo), "--strip-components=1"],
                           check=True)
            if port.exists():
                shutil.rmtree(port)
            novo.rename(port)
            instalar_app()
            self._avanca(0, 1.0)
            jogo = self.raiz / "jogo"
            if self.pasta_jogo:  # pasta ja extraida: so aponta pra ela
                jogo = self.pasta_jogo
                self._avanca(2, 1.0)
            else:
                self._pkgx(1, self.base, jogo)
                self._avanca(1, 1.0)
                if self.update:
                    self._pkgx(2, self.update, jogo)  # a 1.07 por cima da 1.00
                self._avanca(2, 1.0)
            self._avanca(3, 0.5)
            c = ler_config()
            c.update({"versao": (PACOTE / "VERSAO").read_text().strip() if (PACOTE / "VERSAO").exists() else "",
                      "port": str(port), "jogo": str(jogo), "atualizar": c.get("atualizar", True)})
            gravar_config(c)
            self._avanca(3, 1.0)
            self.criar_atalho(self.raiz, port)
            self._avanca(4, 1.0)
            with self.p._trava:
                self.p.pronto = True
        except Exception as e:  # a tela mostra o erro e o log
            import traceback
            traceback.print_exc()
            with self.p._trava:
                self.p.erro = str(e)
