#!/usr/bin/env python3
# Liga o giroscópio e o acelerômetro do controle do Deck (28DE:1205) pra quem lê o controle direto
# (SDL pelo hidraw). No Game Mode a Steam deixa o IMU desligado quando o layout dela não usa giroscópio,
# e o jogo recebe tudo zero. Manda o ajuste SETTING_IMU_MODE (0x30) = gyro + accel crus (0x18) pelo
# relatório de configuração 0x87. Roda como usuário (o hidraw tem ACL pro deck), sem senha.
#   python3 ligar-imu.py                      uma vez
#   python3 ligar-imu.py --manter <log>       espera o jogo registrar o controle no log do emulador
#                                             ("Gamepad registered"), liga, e repete a cada 30 s enquanto
#                                             o jogo estiver aberto
#   Opções pra outro emulador (padrão = shadPS4-plus):
#     --marca <texto>      linha do log que diz que o controle abriu (iss_pc: "Runtime: gamepad connected")
#     --processo <regex>   pgrep -f do jogo aberto (iss_pc: "[o]ut/tlg-probe")
#     --atual <caminho>    link da execução atual; outra execução começou se ele apontar pra outro log
#                          (iss_pc: o próprio log, ".../out/last_run.log")
#     --espera <segundos>  quanto esperar o jogo abrir antes de desistir (padrão 60; iss_pc prepara shaders antes)
# Não mandar enquanto o SDL está abrindo o controle: ele troca relatórios de configuração com o controle
# nessa hora, e um envio no meio faz a abertura falhar ("0 controllers", jogo sem controle; SD-010).
import fcntl
import glob
import os
import subprocess
import sys
import time


def hidiocsfeature(tamanho):
    return (3 << 30) | (tamanho << 16) | (ord('H') << 8) | 0x06


def ligar():
    ligou = False
    for dev in sorted(glob.glob('/dev/hidraw*')):
        try:
            sysfs = f'/sys/class/hidraw/{os.path.basename(dev)}/device'
            uevent = open(f'{sysfs}/uevent').read().upper()
            if '000028DE:00001205' not in uevent:
                continue
            # Só a interface USB 2 (a de configuração) aceita o relatório. Nas outras o ioctl espera 5 s
            # até dar timeout, e nesse tempo o controle fica travado: o jogo congela (SD-011).
            if ':1.2/' not in os.path.realpath(sysfs) + '/':
                continue
            fd = os.open(dev, os.O_RDWR)
            try:
                buf = bytearray(65)  # byte 0 = número do relatório (0)
                buf[1:6] = bytes([0x87, 0x03, 0x30, 0x18, 0x00])
                fcntl.ioctl(fd, hidiocsfeature(len(buf)), buf)
                ligou = True
            finally:
                os.close(fd)
        except OSError:
            pass
    return ligou


def opcao(nome, padrao):
    return sys.argv[sys.argv.index(nome) + 1] if nome in sys.argv else padrao


PROCESSO = opcao('--processo', '^./shadps4')
MARCA = opcao('--marca', 'Gamepad registered')


def jogo_aberto():
    return subprocess.run(['pgrep', '-f', PROCESSO], capture_output=True).returncode == 0


def controle_registrado(log):
    try:
        with open(log, errors='replace') as f:
            return MARCA in f.read()
    except OSError:
        return False


if __name__ == '__main__':
    if '--manter' not in sys.argv:
        print('IMU ligado' if ligar() else 'controle do Deck não encontrado')
        sys.exit(0)
    log = sys.argv[sys.argv.index('--manter') + 1]
    inicio = time.time()
    # Espera o jogo (não o launcher) abrir o controle; o launcher pode ficar aberto bastante tempo.
    while not controle_registrado(log):
        if time.time() - inicio > int(opcao('--espera', '60')) and not jogo_aberto():
            sys.exit(0)
        time.sleep(2)
    time.sleep(3)
    # Sai quando o jogo fecha ou quando outra abertura começou (ela tem o próprio laço).
    atual = os.path.expanduser(opcao('--atual', '~/infamous/ultima-plus.log'))
    alvo = os.path.realpath(log)
    while jogo_aberto() and os.path.realpath(atual) == alvo:
        ligar()
        time.sleep(30)
