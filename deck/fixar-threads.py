#!/usr/bin/env python3
"""Fixa threads do port em núcleos, pelo nome da thread. Roda NO DECK, em segundo plano, pelo rodar-iss.sh.

    fixar-threads.py "<regras>"
Regras separadas por ';', cada uma "nome=cpus" (nome exato da thread, ou prefixo terminado em '*'), e "*=cpus"
pras outras. Ex.: "tlg:DrawRec=6;shadPS4:GpuComm=4;*=0-3,5"
Espera o processo do jogo (out/tlg-probe) aparecer e reaplica a cada 5 s enquanto ele roda (threads novas).
Motivo: no Deck o núcleo físico 0 (CPUs 0-1) roda a ~2,4 GHz e os outros a ~3,48 GHz, e as threads de desenho e de
comandos do port são o caminho crítico do quadro (medições de 2026-10-19 em nativo/medicoes.md).
"""
import os
import subprocess
import sys
import time


def cpus(texto):
    r = set()
    for parte in texto.split(','):
        if '-' in parte:
            a, b = parte.split('-')
            r.update(range(int(a), int(b) + 1))
        elif parte:
            r.add(int(parte))
    return r


def regras(texto):
    out = []
    for item in texto.split(';'):
        if '=' in item:
            nome, c = item.split('=', 1)
            out.append((nome.strip(), cpus(c.strip())))
    return out


def alvo(nome, rs):
    padrao = None
    for r, c in rs:
        if r == '*':
            padrao = c
        elif r.endswith('*') and r != '*' and nome.startswith(r[:-1]):
            return c
        elif r == nome:
            return c
    return padrao


def pid_jogo():
    r = subprocess.run(['pgrep', '-f', '[o]ut/tlg-probe'], capture_output=True, text=True)
    p = r.stdout.split()
    return int(p[0]) if p else None


def main():
    rs = regras(sys.argv[1])
    inicio = time.time()
    pid = None
    while pid is None:
        pid = pid_jogo()
        if pid is None:
            if time.time() - inicio > 1800:
                return
            time.sleep(2)
    feitos = {}
    while os.path.exists(f'/proc/{pid}'):
        try:
            tids = os.listdir(f'/proc/{pid}/task')
        except OSError:
            break
        for tid in tids:
            try:
                nome = open(f'/proc/{pid}/task/{tid}/comm').read().strip()
            except OSError:
                continue
            c = alvo(nome, rs)
            if c and feitos.get(tid) != c:
                try:
                    os.sched_setaffinity(int(tid), c)
                    feitos[tid] = c
                    print(f'{nome} ({tid}) -> {sorted(c)}', flush=True)
                except OSError:
                    pass
        time.sleep(5)


if __name__ == '__main__':
    main()
