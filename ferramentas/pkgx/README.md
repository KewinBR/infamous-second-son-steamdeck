# pkgx

Extrator de `.pkg` de PS4 em linha de comando: o código de extração do [shadPS4](https://github.com/shadps4-emu/shadPS4)
0.6.0 (tag `v.0.6.0`, commit `ec7a5412633f`, GPL-2.0-or-later) num programa pequeno, sem o resto do emulador.

Mudanças em relação ao `pkg.cpp` do shadPS4 0.6.0 (o `patch.py` documenta e aplica):

1. Buffers da decifragem das entradas NP arredondados para 16 bytes (estouro de heap com tamanhos que não são
   múltiplos de 16).
2. Contas de tamanho e posição em 64 bits (arquivos de 2 GB ou mais).
3. Avisos contados na linha `checks:` em vez de silêncio (leitura curta, inflate incompleto, bloco de tamanho errado).
4. Os arquivos vão sempre direto para a pasta de destino.
5. Progresso em cada arquivo (`N/M files, X/Y GiB` na saída de erro), que o instalador mostra na barra.

Compilar (g++ 13 ou mais novo, Crypto++ e zlib):

```bash
bash build.sh
```

O pacote da release usa a versão estática (roda no SteamOS sem instalar nada):

```bash
g++ -std=c++23 -O2 -pthread -Isrc -static main.cpp src/core/file_format/pkg.cpp src/core/file_format/pkg_type.cpp src/core/crypto/crypto.cpp -o pkgx -lcryptopp -lz
```

Uso: `pkgx [-j N] [-l] <arquivo.pkg> <pasta destino>` (`-l` só lista).
