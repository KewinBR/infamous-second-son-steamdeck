#!/usr/bin/env bash
# Build pkgx (needs: g++ >= 13, libcrypto++-dev, zlib1g-dev). Installs to ~/.local/bin/pkgx.
set -euo pipefail
cd "$(dirname "$0")"
g++ -std=c++23 -O2 -pthread -Isrc \
    main.cpp src/core/file_format/pkg.cpp src/core/file_format/pkg_type.cpp src/core/crypto/crypto.cpp \
    -o pkgx -lcryptopp -lz
mkdir -p ~/.local/bin && install -m755 pkgx ~/.local/bin/pkgx
echo "ok: ~/.local/bin/pkgx"
