#!/usr/bin/env python3
"""Pacotes de texto do inFAMOUS Second Son (lang_<idioma>_text*.xpps): extrair e montar.

Só biblioteca padrão. Lê o pacote KCAP do próprio jogador; nada do jogo vai pro git.
Formato e decisões em projetos/infamous/nativo/traducao.md.

    python3 texto_xpps.py info    <pacote.xpps>
    python3 texto_xpps.py extrair <pacote.xpps> <saida.json> [--ref <pacote_ingles.xpps>]
    python3 texto_xpps.py montar  <pacote.xpps> <traducao.json> <saida.xpps>
    python3 texto_xpps.py conferir <pacote.xpps> <traducao.json>   # monta em memória e relê

Resumo do formato (offsets relativos ao início dos dados, `doff`):
- KCAP: cabeçalho 0x98, tabela {6 u64, seções 0x28, itens 12 B, 16 B extras}, dados.
- Todo ponteiro de CPU é um u64 com offset, listado na tabela de ligação (item KNLI, relocação
  tipo 0); tipo 4 = endereço de GPU (T# das texturas de fonte) com o offset nos 32 bits de baixo.
- A tabela de textos é o objeto de classe 0x5d4a6cb5c2b9bf74 (entrada CID = objeto + 0x10):
  +0x30 {ptr, n} categorias {u64 hash, ptr nome}; +0x40 {ptr, n} entradas de 0x20 B
  {u64 hash, ptr nome, 16 B}. O conteúdo vem logo depois do NUL do nome:
    texto simples: string UTF-8 terminada em NUL (menus, HUD, missões: chaves u_*);
    legenda com tempos: alinhado a 2, u16 n, n x {u16 início, u16 fim, u16 offset do texto
    a partir do u16 n}, depois as n strings (diálogos m_*, cenas cb_* ...).
- Montar: os blocos alterados são escritos de novo numa área nova no fim do item dos textos
  (os antigos ficam lá, sem uso) e os ponteiros de nome das entradas passam a apontar pra eles.
  Tudo que vem depois é deslocado e a tabela de ligação é refeita.
"""
from __future__ import annotations

import json
import re
import struct
import sys
from collections import OrderedDict

STRING_TABLE_CLASS = 0x5D4A6CB5C2B9BF74

TAG_ILNK, TAG_CID, TAG_END = b"KNLI", b" DIC", b" DNE"
KNOWN_TAGS = {b"KNLI", b" DIC", b"KNLX", b"PYTO", b"PLPS", b" DNE"}
LINK_ITEM_TYPE = 2


class FormatoErro(ValueError):
    pass


# ---------------------------------------------------------------- KCAP

class Kcap:
    def __init__(self, raw: bytes):
        if raw[:4] != b"KCAP":
            raise FormatoErro("não é um pacote KCAP")
        self.header = bytearray(raw[:0x98])
        self.table_off, self.table_size = struct.unpack_from("<II", raw, 0x18)
        self.doff, self.dsize = struct.unpack_from("<II", raw, 0x28)
        h = struct.unpack_from("<6Q", raw, self.table_off)
        self.thead = list(h)
        nsec, nitem = h[1], h[3]
        pos = self.table_off + 48
        self.sections = []
        for _ in range(nsec):
            self.sections.append(list(struct.unpack_from("<IIIIQQQ", raw, pos)))
            pos += 40
        self.items = []
        for _ in range(nitem):
            self.items.append(list(struct.unpack_from("<III", raw, pos)))   # size, off, flags
            pos += 12
        self.tail = raw[pos:self.doff]      # 16 B extras (e o que mais houver até doff)
        self.data = bytearray(raw[self.doff:self.doff + self.dsize])
        if len(self.data) != self.dsize or self.doff + self.dsize != len(raw):
            raise FormatoErro("tamanho dos dados não bate com o arquivo")

    def serialize(self) -> bytes:
        table = bytearray(struct.pack("<6Q", *self.thead))
        for s in self.sections:
            table += struct.pack("<IIIIQQQ", *s)
        for it in self.items:
            table += struct.pack("<III", *it)
        table += self.tail
        head = bytearray(self.header)
        if self.table_off + len(table) != self.doff:
            raise FormatoErro("tabela mudou de tamanho")
        struct.pack_into("<II", head, 0x28, self.doff, len(self.data))
        return bytes(head) + bytes(raw_pad(self.table_off - len(head))) + bytes(table) + bytes(self.data)

    def u64(self, off):
        return struct.unpack_from("<Q", self.data, off)[0]

    def u32(self, off):
        return struct.unpack_from("<I", self.data, off)[0]

    def item_of(self, off):
        for i, (size, o, _fl) in enumerate(self.items):
            if o <= off < o + size:
                return i
        return None


def raw_pad(n):
    return b"\0" * n


# ---------------------------------------------------------------- KNLI (tabela de ligação)

class Links:
    """Uma tabela de ligação: relocações por tipo e CID. Só os blocos que existem nos pacotes de
    texto (KNLI e " DIC"); qualquer outro bloco faz a ferramenta parar em vez de perder dados."""

    def __init__(self):
        self.order = []          # ordem dos tipos de relocação como no original
        self.relocs = {}         # tipo -> lista de posições
        self.cid = []            # [(local, classe)]
        self.chunk_order = []    # tags na ordem original

    @staticmethod
    def decode(values):
        out, base, cur = [], 0, 0
        for s in values:
            if s >= 0:
                cur = base + 4 * s
                out.append(cur)
            elif s & 0x4000:
                base = (s & 0x3FFF) << 17
            else:
                for _ in range(s & 0x3FFF):
                    cur += 4
                    out.append(cur)
        return out

    @staticmethod
    def encode(positions):
        out, base = [], None
        for p in sorted(positions):
            if p % 4:
                raise FormatoErro(f"relocação desalinhada em {p:#x}")
            b = p >> 17
            if b != base:
                out.append(-0x10000 + (0xC000 | b) if b else -0x10000 + 0xC000)
                base = b
            out.append((p - (b << 17)) // 4)
        return out

    @classmethod
    def parse(cls, data: bytes, off: int, end: int):
        lt = cls()
        pos = off
        while pos + 8 <= end:
            tag = bytes(data[pos:pos + 4])
            (size,) = struct.unpack_from("<I", data, pos + 4)
            p = pos + 8
            if tag not in KNOWN_TAGS:
                raise FormatoErro(f"bloco desconhecido {tag!r} na tabela de ligação")
            lt.chunk_order.append(tag)
            if tag == TAG_END:
                lt.end_pos = p
                return lt
            if tag == TAG_ILNK:
                (n,) = struct.unpack_from("<i", data, p)
                heads = [struct.unpack_from("<ii", data, p + 4 + 8 * i) for i in range(n)]
                sp = p + 4 + 8 * n
                for rtype, count in heads:
                    vals = struct.unpack_from(f"<{count}h", data, sp)
                    lt.order.append(rtype)
                    lt.relocs[rtype] = cls.decode(vals)
                    sp += 2 * count
                lt.ilnk_raw = bytes(data[p:p + size])
            elif tag == TAG_CID:
                (n,) = struct.unpack_from("<Q", data, p)
                lt.cid = [struct.unpack_from("<QQ", data, p + 8 + 16 * i) for i in range(n)]
                lt.cid_raw_size = size
            else:
                raise FormatoErro(f"bloco {tag!r} não suportado (pacote de texto inesperado)")
            pos = p + size
        raise FormatoErro("tabela de ligação sem fim")

    def build(self) -> bytes:
        out = bytearray()
        for tag in self.chunk_order:
            if tag == TAG_ILNK:
                body = bytearray(struct.pack("<i", len(self.order)))
                streams = [self.encode(self.relocs[t]) for t in self.order]
                for t, s in zip(self.order, streams):
                    body += struct.pack("<ii", t, len(s))
                for s in streams:
                    body += struct.pack(f"<{len(s)}h", *s)
                while len(body) % 4:
                    body += b"\0"
            elif tag == TAG_CID:
                body = bytearray(struct.pack("<Q", len(self.cid)))
                for local, cls_ in self.cid:
                    body += struct.pack("<QQ", local, cls_)
            elif tag == TAG_END:
                out += TAG_END + struct.pack("<I", 0)
                continue
            out += tag + struct.pack("<I", len(body)) + body
        return bytes(out)


def find_links(k: Kcap):
    found = []
    for i, (size, off, flags) in enumerate(k.items):
        if (flags >> 16) == LINK_ITEM_TYPE and k.data[off:off + 4] == TAG_ILNK:
            found.append(i)
    if len(found) != 1:
        raise FormatoErro(f"esperava 1 tabela de ligação, achei {len(found)}")
    i = found[0]
    size, off, _ = k.items[i]
    return i, Links.parse(k.data, off, off + size)


# ---------------------------------------------------------------- tabela de textos

def cstr_end(data, off):
    end = data.index(b"\0", off)
    return end


class Entrada:
    __slots__ = ("idx", "hash", "slot", "name_off", "name", "kind", "lines", "texts", "extra",
                 "block_end")


def ler_bloco(data, name_off):
    """(nome, tipo, linhas, textos, fim). tipo 'simples' ou 'tempos'; linhas = [(ini, fim)]."""
    nul = cstr_end(data, name_off)
    name = data[name_off:nul].decode("ascii")
    p = nul + 1
    q = (p + 2) & ~1          # fala: pelo menos 1 byte depois do NUL, u16 alinhado a 2
    # legenda com tempos?
    if q + 2 <= len(data):
        (n,) = struct.unpack_from("<H", data, q)
        if n == 0 and data[p] == 0:
            return name, "tempos", [], [], q + 2      # fala sem legenda
        if 0 < n < 2000 and q + 2 + 6 * n <= len(data):
            trip = [struct.unpack_from("<HHH", data, q + 2 + 6 * i) for i in range(n)]
            if trip[0][2] == 2 + 6 * n:
                texts, lines, ok, cur = [], [], True, q + 2 + 6 * n
                for a, b, o in trip:
                    if q + o != cur:
                        ok = False
                        break
                    e = cstr_end(data, cur)
                    texts.append(data[cur:e].decode("utf-8"))
                    lines.append((a, b))
                    cur = e + 1
                if ok:
                    return name, "tempos", lines, texts, cur
    e = cstr_end(data, p)
    return name, "simples", None, [data[p:e].decode("utf-8")], e + 1


def montar_bloco(start, name, kind, lines, texts):
    """Bytes do bloco cujo nome começa no offset `start`."""
    b = bytearray(name.encode("ascii") + b"\0")
    if kind == "simples":
        b += texts[0].encode("utf-8") + b"\0"
        return bytes(b)
    p = start + len(b)
    b += b"\0" * (((p + 2) & ~1) - p)
    n = len(texts)
    enc = [t.encode("utf-8") + b"\0" for t in texts]
    o = 2 + 6 * n
    head = bytearray(struct.pack("<H", n))
    for (a, e), t in zip(lines, enc):
        if o > 0xFFFF:
            raise FormatoErro(f"bloco {name} passa de 64 KiB")
        head += struct.pack("<HHH", a, e, o)
        o += len(t)
    return bytes(b + head + b"".join(enc))


class Pacote:
    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            self.raw = f.read()
        self.k = Kcap(self.raw)
        self.link_item, self.links = find_links(self.k)
        roots = [local for local, cls_ in self.links.cid if cls_ == STRING_TABLE_CLASS]
        if len(roots) != 1:
            raise FormatoErro(f"esperava 1 tabela de textos, achei {len(roots)}")
        self.root = roots[0] - 0x10
        k = self.k
        self.ptr_cat, self.n_cat = k.u64(self.root + 0x30), k.u64(self.root + 0x38)
        self.ptr_ent, self.n_ent = k.u64(self.root + 0x40), k.u64(self.root + 0x48)
        self.entradas = []
        for i in range(self.n_ent):
            e = Entrada()
            base = self.ptr_ent + 0x20 * i
            e.idx, e.hash, e.slot = i, k.u64(base), base + 8
            e.name_off = k.u64(base + 8)
            e.extra = bytes(k.data[base + 16:base + 32])
            e.name, e.kind, e.lines, e.texts, e.block_end = ler_bloco(k.data, e.name_off)
            self.entradas.append(e)
        # variáveis: +0x60 {ptr, n} de {u64 hash da entrada, ptr, u32 n, u32 0}; cada uma aponta pra n x
        # {u64 posição em BYTES no texto UTF-8, u64 hash da variável}: onde o jogo encaixa o valor
        self.vars = {}      # hash da entrada -> [(offset do campo posição, posição)]
        pv, nv = k.u64(self.root + 0x60), k.u64(self.root + 0x68)
        for i in range(nv):
            h, q, c, _ = struct.unpack_from("<QQII", k.data, pv + 24 * i)
            self.vars[h] = [(q + 16 * j, k.u64(q + 16 * j)) for j in range(c)]

    def por_nome(self):
        return {e.name: e for e in self.entradas}

    # ------------------------------------------------ montar
    def posicoes(self, e):
        return [pos for _, pos in self.vars.get(e.hash, [])]

    def montar(self, novos: dict, posicoes: dict = None) -> bytes:
        """novos: nome -> lista de textos (mesmo número de linhas do original);
        posicoes: nome -> posições em bytes das variáveis (entradas da tabela +0x60)."""
        posicoes = posicoes or {}
        mud_pos = []
        for e in self.entradas:
            ps = posicoes.get(e.name)
            if ps is not None and ps != self.posicoes(e):
                if len(ps) != len(self.vars.get(e.hash, [])):
                    raise FormatoErro(f"{e.name}: {len(ps)} variáveis, original tem {len(self.vars.get(e.hash, []))}")
                mud_pos.append((e, ps))
        k = Kcap(self.raw)
        lt = Links.parse(k.data, k.items[self.link_item][1],
                         k.items[self.link_item][1] + k.items[self.link_item][0])
        mudar = []
        for e in self.entradas:
            t = novos.get(e.name)
            if t is None or list(t) == e.texts:
                continue
            if len(t) != len(e.texts):
                raise FormatoErro(f"{e.name}: {len(t)} linhas, original tem {len(e.texts)}")
            mudar.append((e, t))
        if not mudar:
            if not mud_pos:
                return self.raw
            raise FormatoErro("posições de variável mudaram sem o texto mudar")
        # onde inserir: no fim do item que guarda os nomes
        str_item = k.item_of(self.entradas[0].name_off)
        for e, _ in mudar:
            if k.item_of(e.name_off) != str_item:
                raise FormatoErro("nomes espalhados em mais de um item")
        size, ioff, _ = k.items[str_item]
        X = ioff + size
        blob = bytearray()
        novo_off = {}
        for e, t in mudar:
            # mesmo resto módulo 16 do nome original: preserva qualquer regra de alinhamento
            while (X + len(blob)) % 16 != e.name_off % 16:
                blob += b"\0"
            novo_off[e.slot] = X + len(blob)
            blob += montar_bloco(X + len(blob), e.name, e.kind, e.lines, t)
        D = (len(blob) + 0xFF) & ~0xFF
        blob += b"\0" * (D - len(blob))
        sh = lambda v: v + D if v >= X else v

        # 1) relocações: posições e valores
        newdata = bytearray(k.data[:X]) + blob + k.data[X:]
        for rtype, pos in lt.relocs.items():
            if rtype not in (0, 4):
                raise FormatoErro(f"relocação tipo {rtype} não suportada")
            npos = []
            for p in pos:
                np_ = sh(p)
                if rtype == 0:
                    v = struct.unpack_from("<Q", newdata, np_)[0]
                    struct.pack_into("<Q", newdata, np_, sh(v))
                else:
                    v = struct.unpack_from("<I", newdata, np_)[0]
                    struct.pack_into("<I", newdata, np_, sh(v))
                npos.append(np_)
            lt.relocs[rtype] = npos
        lt.cid = [(sh(local), c) for local, c in lt.cid]
        # 2) ponteiros de nome das entradas alteradas
        for slot, off in novo_off.items():
            struct.pack_into("<Q", newdata, sh(slot), off)
        # 2b) posições das variáveis (valores simples, sem relocação)
        for e, ps in mud_pos:
            for (campo, _), pos in zip(self.vars[e.hash], ps):
                struct.pack_into("<Q", newdata, sh(campo), pos)
        # 3) itens e seções
        for it in k.items:
            s, o, _ = it
            if o >= X:
                it[1] = o + D
            elif o < X <= o + s:
                it[0] = s + D
        for sec in k.sections:
            # seção: flags, size, off, ...
            if sec[2] >= X:
                sec[2] += D
            elif sec[2] < X <= sec[2] + sec[1]:
                sec[1] += D
        # 4) tabela de ligação refeita (último item, última seção)
        li = k.items[self.link_item]
        if li[1] + li[0] != len(newdata):
            raise FormatoErro("a tabela de ligação não é o último item")
        nl = lt.build()
        newlink = nl + b"\0" * ((-len(nl)) % 8)
        newdata = newdata[:li[1]] + newlink
        li[0] = len(newlink)
        last = k.sections[-1]
        if last[2] != li[1]:
            raise FormatoErro("a tabela de ligação não está numa seção própria no fim")
        last[1] = len(newlink)
        k.data = newdata
        return k.serialize()


# ---------------------------------------------------------------- comandos

def cmd_info(path):
    p = Pacote(path)
    k = p.k
    print(f"{path}: doff {k.doff:#x}, dados {k.dsize} B, {len(k.sections)} seções, {len(k.items)} itens")
    for i, (s, o, fl) in enumerate(k.items):
        print(f"  item {i:2d} off {o:#9x} tam {s:8d} flags {fl:#08x}")
    print(f"  relocações: " + ", ".join(f"tipo {t}: {len(v)}" for t, v in p.links.relocs.items())
          + f"; CID {len(p.links.cid)}")
    kinds = {}
    for e in p.entradas:
        kinds[e.kind] = kinds.get(e.kind, 0) + 1
    print(f"  tabela de textos em {p.root:#x}: {p.n_cat} categorias, {p.n_ent} entradas {kinds}, "
          f"{sum(len(e.texts) for e in p.entradas)} strings")
    # conferência: os blocos cobrem a área sem buracos com dados
    offs = sorted(p.entradas, key=lambda e: e.name_off)
    gaps = 0
    for a, b in zip(offs, offs[1:]):
        gap = bytes(k.data[a.block_end:b.name_off])
        if gap.strip(b"\0"):
            gaps += 1
            if gaps <= 5:
                print(f"  dados entre {a.name} e {b.name}: {gap[:60]!r}")
    print(f"  buracos com dados entre blocos: {gaps}")


VAR = re.compile("⟦V(\\d+)⟧")


def por_vars(texto, posicoes):
    """Põe ⟦V1⟧, ⟦V2⟧... (na ordem da tabela) nas posições em bytes onde o jogo encaixa cada valor."""
    b = texto.encode("utf-8")
    out = bytearray()
    for i in range(len(b) + 1):
        for j, pos in enumerate(posicoes):
            if pos == i or (i == len(b) and pos > len(b)):
                out += f"⟦V{j + 1}⟧".encode("utf-8")
        if i < len(b):
            out += b[i:i + 1]
    return out.decode("utf-8")


def tirar_vars(texto, n):
    """(texto limpo, posições em bytes) a partir de um texto com ⟦V1⟧..⟦Vn⟧, cada um exatamente uma vez."""
    achadas = [int(m.group(1)) for m in VAR.finditer(texto)]
    if sorted(achadas) != list(range(1, n + 1)):
        raise FormatoErro(f"esperava ⟦V1⟧..⟦V{n}⟧ uma vez cada, achei {achadas} em {texto!r}")
    pos = [0] * n
    limpo = bytearray()
    resto = texto
    while True:
        m = VAR.search(resto)
        if not m:
            limpo += resto.encode("utf-8")
            break
        limpo += resto[:m.start()].encode("utf-8")
        pos[int(m.group(1)) - 1] = len(limpo)
        resto = resto[m.end():]
    return limpo.decode("utf-8"), pos


def cmd_extrair(path, out, ref=None):
    p = Pacote(path)
    rp = Pacote(ref) if ref else None
    r = rp.por_nome() if rp else {}
    res = OrderedDict()
    for e in p.entradas:
        re_ = r.get(e.name)
        for i, t in enumerate(e.texts):
            key = e.name if e.kind == "simples" else f"{e.name}#{i}"
            item = OrderedDict(pt=por_vars(t, p.posicoes(e)) if e.kind == "simples" else t)
            if re_ is not None and len(re_.texts) == len(e.texts):
                item["en"] = por_vars(re_.texts[i], rp.posicoes(re_)) if re_.kind == "simples" else re_.texts[i]
            item["br"] = ""
            res[key] = item
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"{len(res)} strings de {len(p.entradas)} entradas -> {out}")


def carregar_traducao(p: Pacote, path):
    with open(path, encoding="utf-8") as f:
        tr = json.load(f)
    novos, posicoes = {}, {}
    for e in p.entradas:
        out = []
        for i, t in enumerate(e.texts):
            key = e.name if e.kind == "simples" else f"{e.name}#{i}"
            item = tr.get(key)
            br = item.get("br") if isinstance(item, dict) else item
            n = len(p.vars.get(e.hash, []))
            if br and e.kind == "simples" and (n or VAR.search(br)):
                try:
                    br, posicoes[e.name] = tirar_vars(br, n)
                except FormatoErro as ex:
                    raise FormatoErro(f"{key}: {ex}") from None
            out.append(br if br else t)
        novos[e.name] = out
    return novos, posicoes


def cmd_montar(path, trad, out):
    p = Pacote(path)
    novos, posicoes = carregar_traducao(p, trad)
    data = p.montar(novos, posicoes)
    with open(out, "wb") as f:
        f.write(data)
    print(f"{out}: {len(data)} B (original {len(p.raw)} B)")
    return data


def cmd_conferir(path, trad):
    import os
    import tempfile
    p = Pacote(path)
    novos, posicoes = carregar_traducao(p, trad)
    data = p.montar(novos, posicoes)
    fd, tmp = tempfile.mkstemp(suffix=".xpps")
    os.write(fd, data)
    os.close(fd)
    try:
        q = Pacote(tmp)
    finally:
        os.unlink(tmp)
    erros = 0
    for a, b in zip(p.entradas, q.entradas):
        if (a.hash, a.name, a.kind, a.lines, a.extra) != (b.hash, b.name, b.kind, b.lines, b.extra) \
                or b.texts != novos[a.name] \
                or q.posicoes(b) != posicoes.get(a.name, p.posicoes(a)):
            erros += 1
            if erros < 5:
                print("diferente:", a.name)
    # posição de variável fora do texto ou no meio de um caractere UTF-8 = valor some ou texto quebra
    for e in q.entradas:
        for pos in q.posicoes(e):
            b = e.texts[0].encode("utf-8") if e.texts else b""
            if pos > len(b) or (pos < len(b) and (b[pos] & 0xC0) == 0x80):
                erros += 1
                print(f"variável fora do lugar: {e.name} pos {pos} em {e.texts!r}")
    # o resto dos dados não pode mudar: compara todos os ponteiros relocados (alvo deslocado)
    print(f"entradas {len(q.entradas)}, erros {erros}, relocações "
          + ", ".join(f"{t}:{len(v)}" for t, v in q.links.relocs.items()))
    return erros == 0


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "info":
        cmd_info(argv[2])
    elif cmd == "extrair":
        ref = argv[argv.index("--ref") + 1] if "--ref" in argv else None
        cmd_extrair(argv[2], argv[3], ref)
    elif cmd == "montar":
        cmd_montar(argv[2], argv[3], argv[4])
    elif cmd == "conferir":
        return 0 if cmd_conferir(argv[2], argv[3]) else 1
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
