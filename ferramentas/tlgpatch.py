#!/usr/bin/env python3
"""Arte nova + original (PNG) -> .tlgpatch: so os blocos BC3 que mudaram, por mip.

O port acha a textura do jogo pelo XXH3 dos bytes dela na memoria, desfaz o tiling dela e troca so os blocos deste
arquivo antes de subir para a GPU (texture_cache.cpp, TLG_TEXTURE_EASTER_DIR). O resto da textura vem do jogo da
propria pessoa, entao o arquivo leva so o que e nosso (os blocos redesenhados).

    python3 tlgpatch.py <nova.png> <original.png> <hash-hex> <mips> <saida.tlgpatch> [--virar]
      original.png  a mip 0 da textura do jogo (so para saber quais blocos mudaram; nao vai no arquivo)
      --virar       as duas imagens estao de pe e o jogo guarda a textura de ponta cabeca

Formato: "TLGPAT1\\0", u64 hash, u32 largura, altura, mips; depois, por mip: u32 n, n x u32 indice do bloco (ordem
linear, linha a linha) e n x 16 bytes de bloco BC3.
"""
import struct
import sys

import numpy as np
from PIL import Image


def blocos(img):
    """(H, W, 4) uint8 -> (nby, nbx, 16, 4) float, com a borda repetida ate multiplo de 4."""
    h, w = img.shape[:2]
    ph, pw = -h % 4, -w % 4
    if ph or pw:
        img = np.pad(img, ((0, ph), (0, pw), (0, 0)), mode="edge")
    h, w = img.shape[:2]
    b = img.reshape(h // 4, 4, w // 4, 4, 4).transpose(0, 2, 1, 3, 4)
    return b.reshape(h // 4, w // 4, 16, 4).astype(np.float32)


def rgb565(c):
    r = np.round(c[..., 0] * 31 / 255).astype(np.uint32)
    g = np.round(c[..., 1] * 63 / 255).astype(np.uint32)
    b = np.round(c[..., 2] * 31 / 255).astype(np.uint32)
    return (r << 11) | (g << 5) | b


def de565(v):
    r = ((v >> 11) & 31) * 255 / 31
    g = ((v >> 5) & 63) * 255 / 63
    b = (v & 31) * 255 / 31
    return np.stack([r, g, b], -1).astype(np.float32)


def bc3(img):
    """Imagem RGBA -> (nby, nbx, 16) uint8 de blocos BC3."""
    b = blocos(img)
    nby, nbx = b.shape[:2]
    rgb, a = b[..., :3], b[..., 3]
    a0, a1 = a.max(-1), a.min(-1)
    niveis = np.stack([a0, a1] + [((7 - i) * a0 + i * a1) / 7 for i in range(1, 7)], -1)
    ai = np.abs(a[..., :, None] - niveis[..., None, :]).argmin(-1).astype(np.uint64)
    ai[a0 == a1] = 0
    abits = np.zeros((nby, nbx), np.uint64)
    for p in range(16):
        abits |= ai[..., p] << np.uint64(3 * p)
    media = rgb.mean(-2, keepdims=True)
    d = rgb - media
    cov = np.einsum("...pi,...pj->...ij", d, d)
    eixo = np.ones((nby, nbx, 3), np.float32)
    for _ in range(8):
        eixo = np.einsum("...ij,...j->...i", cov, eixo)
        eixo /= np.linalg.norm(eixo, axis=-1, keepdims=True) + 1e-6
    proj = np.einsum("...pi,...i->...p", d, eixo)
    cmax = np.take_along_axis(rgb, proj.argmax(-1)[..., None, None].repeat(3, -1), -2)[..., 0, :]
    cmin = np.take_along_axis(rgb, proj.argmin(-1)[..., None, None].repeat(3, -1), -2)[..., 0, :]
    c0, c1 = rgb565(cmax), rgb565(cmin)
    troca = c0 < c1
    c0, c1 = np.where(troca, c1, c0), np.where(troca, c0, c1)
    p0, p1 = de565(c0), de565(c1)
    paleta = np.stack([p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3], -2)
    dist = ((rgb[..., :, None, :] - paleta[..., None, :, :]) ** 2).sum(-1)
    ci = dist.argmin(-1).astype(np.uint32)
    ci[c0 == c1] = 0
    cbits = np.zeros((nby, nbx), np.uint32)
    for p in range(16):
        cbits |= ci[..., p] << np.uint32(2 * p)
    out = np.zeros((nby, nbx, 16), np.uint8)
    out[..., 0] = np.round(a0).astype(np.uint8)
    out[..., 1] = np.round(a1).astype(np.uint8)
    for k in range(6):
        out[..., 2 + k] = ((abits >> np.uint64(8 * k)) & np.uint64(255)).astype(np.uint8)
    out[..., 8:10] = np.stack([c0 & 255, c0 >> 8], -1).astype(np.uint8)
    out[..., 10:12] = np.stack([c1 & 255, c1 >> 8], -1).astype(np.uint8)
    for k in range(4):
        out[..., 12 + k] = ((cbits >> np.uint32(8 * k)) & 255).astype(np.uint8)
    return out


def patch(nova, original, h, mips, virar=False, limiar=3):
    """Devolve os bytes do .tlgpatch e quantos blocos mudaram."""
    if virar:
        nova, original = (i.transpose(Image.FLIP_TOP_BOTTOM) for i in (nova, original))
    w, hh = nova.size
    corpo, total = b"", 0
    for m in range(mips):
        mw, mh = max(w >> m, 1), max(hh >> m, 1)
        n = nova if m == 0 else nova.resize((mw, mh), Image.BOX)
        o = original if m == 0 else original.resize((mw, mh), Image.BOX)
        bn, bo = blocos(np.asarray(n)), blocos(np.asarray(o))
        mudou = np.abs(bn - bo).max((-1, -2)) > limiar
        idx = np.flatnonzero(mudou).astype(np.uint32)
        blk = bc3(np.asarray(n)).reshape(-1, 16)[idx]
        corpo += struct.pack("<I", len(idx)) + idx.tobytes() + blk.tobytes()
        total += len(idx)
    return b"TLGPAT1\0" + struct.pack("<QIII", h, w, hh, mips) + corpo, total


def main():
    a = sys.argv
    nova = Image.open(a[1]).convert("RGBA")
    original = Image.open(a[2]).convert("RGBA")
    dados, n = patch(nova, original, int(a[3], 16), int(a[4]), "--virar" in a)
    with open(a[5], "wb") as f:
        f.write(dados)
    print("ok", a[5], f"{nova.size[0]}x{nova.size[1]}", n, "blocos", len(dados), "bytes")


if __name__ == "__main__":
    main()
