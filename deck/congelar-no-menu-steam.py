#!/usr/bin/env python3
# Congela o jogo enquanto o menu da Steam (botão Steam) ou o menu rápido ("...") estiver por cima, no Game Mode,
# como o PS4 suspende o jogo no botão PS: imagem, som e controle param; ao voltar, o jogo segue de onde estava.
# Sinal: a raiz do X do gamescope (:0) tem GAMESCOPE_FOCUSED_APP = appid do jogo enquanto o jogo tem o foco e 769
# (a Steam) com o menu aberto (medido em 2026-10-19). Congela com SIGSTOP e solta com SIGCONT.
# Sair do jogo pelo menu da Steam com ele congelado: a Steam manda SIGTERM, que fica pendente num processo parado;
# o laço vê o sinal pendente (/proc/<pid>/status, ShdPnd/SigPnd) e solta o jogo pra ele poder fechar.
#   congelar-no-menu-steam.py <appid do jogo> <regex do processo (pgrep -f)> [arquivo de pausa]
# Com o arquivo de pausa (TLG_STEAM_PAUSE_FILE do port, iss-13): em vez de SIGSTOP, cria o arquivo enquanto o menu
# da Steam cobre o jogo e apaga ao voltar; o próprio port congela as threads do jogo, escurece a tela com fade e,
# na volta, espera um instante e tira o escurecimento antes de soltar o jogo (o mesmo efeito do menu do View).
# Roda como usuário, sem senha (o processo do jogo é do mesmo usuário). Sai sozinho quando o jogo fecha.
import os
import select
import signal
import subprocess
import sys
import time

STEAM = 769
appid, padrao = int(sys.argv[1]), sys.argv[2]
arquivo = sys.argv[3] if len(sys.argv) > 3 else None


def pids():
    r = subprocess.run(['pgrep', '-f', padrao], capture_output=True, text=True)
    return [int(p) for p in r.stdout.split()]


FECHAR = sum(1 << (s - 1) for s in (signal.SIGHUP, signal.SIGINT, signal.SIGQUIT, signal.SIGTERM))


def sinal_pendente(pid):
    """Pedido de fechar pendente (o próprio SIGSTOP aparece pendente por um instante e não conta)."""
    try:
        for linha in open(f'/proc/{pid}/status'):
            if linha.startswith(('ShdPnd:', 'SigPnd:')) and int(linha.split()[1], 16) & FECHAR:
                return True
    except OSError:
        pass
    return False


def foco():
    r = subprocess.run(['xprop', '-root', 'GAMESCOPE_FOCUSED_APP'], capture_output=True, text=True,
                       env={**os.environ, 'DISPLAY': ':0'})
    try:
        return int(r.stdout.rsplit('=', 1)[1])
    except (IndexError, ValueError):
        return None


def soltar(lista):
    for p in lista:
        try:
            os.kill(p, signal.SIGCONT)
        except OSError:
            pass


def log(msg):
    print(time.strftime('%T'), msg, flush=True)


inicio = time.time()
while not pids():                       # espera o jogo abrir (o launcher pode demorar)
    if time.time() - inicio > 1800:
        sys.exit(0)
    time.sleep(1)
# O spy avisa a cada mudança da propriedade; o tempo limite do select serve pra conferir sinais pendentes.
spy = subprocess.Popen(['xprop', '-root', '-spy', 'GAMESCOPE_FOCUSED_APP'], stdout=subprocess.PIPE, text=True,
                       env={**os.environ, 'DISPLAY': ':0'})
congelado = []
armado = False   # só age depois de ver o jogo com o foco (na carga o foco ainda é da Steam)
sem_jogo = None  # o processo troca na abertura (preparação -> jogo): só sai depois de 15 s sem nenhum
log(f'vigiando appid {appid}')
while True:
    vivos = pids()
    if not vivos:
        sem_jogo = sem_jogo or time.time()
        if time.time() - sem_jogo > 15:
            break
    else:
        sem_jogo = None
    if congelado and any(sinal_pendente(p) for p in congelado):
        soltar(congelado)
        log('sinal pendente (fechando o jogo): solto')
        congelado = []
    pronto, _, _ = select.select([spy.stdout], [], [], 0.25)
    if not pronto:
        continue
    linha = spy.stdout.readline()
    if not linha:
        break
    try:
        atual = int(linha.rsplit('=', 1)[1])
    except (IndexError, ValueError):
        continue
    if atual == appid:
        armado = True
    if atual == STEAM and armado and vivos and not congelado:
        congelado = vivos
        if arquivo:
            open(arquivo, 'w').close()
        else:
            for p in congelado:
                try:
                    os.kill(p, signal.SIGSTOP)
                except OSError:
                    pass
        log(f'menu da Steam aberto: jogo congelado {congelado}' + (' (pelo port)' if arquivo else ''))
    elif atual == appid and congelado:
        if arquivo:
            try:
                os.remove(arquivo)
            except OSError:
                pass
        else:
            soltar(congelado)
        log('de volta ao jogo: solto')
        congelado = []
if arquivo:
    try:
        os.remove(arquivo)
    except OSError:
        pass
else:
    soltar(congelado)
spy.terminate()
log('jogo fechou')
