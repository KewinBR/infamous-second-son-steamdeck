#!/usr/bin/env python3
"""Adapt shadPS4 v.0.6.0 pkg.h/pkg.cpp for the standalone pkgx CLI.

Changes (decryption / decompression / layout logic is untouched):
- pkg.h: drop trp.h + TRP member (trophies, not needed); add warning counters.
- pkg.cpp: drop the logging include (fmt::UTF only used in the uroot path choice);
  uroot files always go to the given output dir (the GUI got the same result:
  <install>/<TITLEID> or <...>-UPDATE);
  ExtractFiles: 64-bit size math (original used int for size/offsets, signed overflow
  for files >= 2 GiB), checks for short reads, inflate errors and unexpected block
  sizes (counted + reported instead of silently writing stale data).
"""
import re, sys, pathlib

d = pathlib.Path(sys.argv[1])
h = (d / "pkg.h").read_text()
h = h.replace('#include "trp.h"\n', '#include <atomic>\n')
h = h.replace("    TRP trp;\n", "")
h = h.replace("    std::vector<u8> sfo;\n",
              "    std::vector<u8> sfo;\n"
              "    static inline std::atomic<u64> warn_short_read{0}, warn_inflate{0}, warn_block{0};\n"
              "    std::string_view GetFileName(int index) { return fsTable[index].name; }\n"
              "    u32 GetFileType(int index) { return fsTable[index].type; }\n"
              "    std::filesystem::path GetFilePath(int index) { return extractPaths.at(fsTable[index].inode); }\n"
              "    u64 GetFileSize(int index) { return fsTable[index].type == PFS_FILE ? (u64)iNodeBuf[fsTable[index].inode].Size : 0; }\n")
assert "TRP" not in h
(d / "pkg.h").write_text(h)

c = (d / "pkg.cpp").read_text()
c = c.replace('#include "common/logging/formatter.h"\n', '#include <cstring>\n#include <span>\n')

old_uroot = re.search(r"auto parent_path = extract_path\.parent_path\(\);.*?\n(\s*)uroot_reached = false;",
                      c, re.S)
assert old_uroot
c = c.replace(old_uroot.group(0),
              "extractPaths[ndinode_counter] = extract_path;\n" + old_uroot.group(1) + "uroot_reached = false;")

# Inflate with result check.
c = c.replace("""static void DecompressPFSC(std::span<char> compressed_data, std::span<char> decompressed_data) {""",
              """static bool DecompressPFSC(std::span<char> compressed_data, std::span<char> decompressed_data) {""")
c = c.replace("""    if (inflate(&decompressStream, Z_FINISH)) {
    }
    if (inflateEnd(&decompressStream) != Z_OK) {
        // std::cerr << "Error ending zlib inflate" << std::endl;
    }
}""", """    const int ret = inflate(&decompressStream, Z_FINISH);
    const bool ok = ret == Z_STREAM_END && decompressStream.total_out == decompressed_data.size();
    inflateEnd(&decompressStream);
    return ok;
}""")

start = c.index("void PKG::ExtractFiles(const int index) {")
c = c[:start] + r'''void PKG::ExtractFiles(const int index) {
    const u32 inode_number = fsTable[index].inode;
    const u32 inode_type = fsTable[index].type;

    if (inode_type == PFS_FILE) {
        const u64 sector_loc = iNodeBuf[inode_number].loc;
        const u64 nblocks = iNodeBuf[inode_number].Blocks;
        const u64 bsize = iNodeBuf[inode_number].Size;
        const auto& out_path = extractPaths.at(inode_number);

        Common::FS::IOFile inflated;
        inflated.Open(out_path, Common::FS::FileAccessMode::Write);

        Common::FS::IOFile pkgFile; // Open the file for each iteration to avoid conflict.
        pkgFile.Open(pkgpath, Common::FS::FileAccessMode::Read);

        u64 size_decompressed = 0;
        std::vector<char> compressedData;
        std::vector<char> decompressedData(0x10000);

        const u64 pfsc_buf_size = 0x11000; // extra 0x1000
        std::vector<u8> pfsc(pfsc_buf_size);
        std::vector<u8> pfs_decrypted(pfsc_buf_size);

        for (u64 j = 0; j < nblocks; j++) {
            const u64 sectorOffset = sectorMap.at(sector_loc + j); // offset into PFSC image
            const u64 sectorSize = sectorMap.at(sector_loc + j + 1) - sectorOffset;
            const u64 abs = pfsc_offset + sectorOffset;      // offset into pfs image
            const u64 fileOffset = pkgheader.pfs_image_offset + abs;
            const u64 currentSector1 = abs / 0x1000; // XTS sector size is 0x1000
            const u64 previousData = abs & 0xFFF;

            pkgFile.Seek(fileOffset - previousData);
            const u64 want = std::min<u64>(pfsc_buf_size, (previousData + sectorSize + 0xFFF) & ~u64(0xFFF));
            const u64 got = pkgFile.ReadRaw<u8>(pfsc.data(), pfsc_buf_size);
            if (got < want || sectorSize > 0x10000 || sectorSize == 0) {
                if (got < want) {
                    ++warn_short_read;
                    std::fprintf(stderr, "pkgx: WARN short read (%llu < %llu) in %s block %llu\n",
                                 (unsigned long long)got, (unsigned long long)want,
                                 out_path.c_str(), (unsigned long long)j);
                } else {
                    ++warn_block;
                    std::fprintf(stderr, "pkgx: WARN block size 0x%llx in %s block %llu (zero-filled)\n",
                                 (unsigned long long)sectorSize, out_path.c_str(),
                                 (unsigned long long)j);
                }
            }

            PKG::crypto.decryptPFS(dataKey, tweakKey, pfsc, pfs_decrypted, currentSector1);

            if (sectorSize == 0x10000) { // Uncompressed data
                std::memcpy(decompressedData.data(), pfs_decrypted.data() + previousData, 0x10000);
            } else if (sectorSize > 0 && sectorSize < 0x10000) { // Compressed data
                compressedData.resize(sectorSize);
                std::memcpy(compressedData.data(), pfs_decrypted.data() + previousData, sectorSize);
                if (!DecompressPFSC(compressedData, decompressedData)) {
                    // Last block of a file may legitimately inflate to less than 0x10000.
                    const u64 need = (j == nblocks - 1) ? bsize - size_decompressed : 0x10000;
                    z_stream zs{};
                    std::vector<char> tmp(0x10000);
                    inflateInit(&zs);
                    zs.next_in = reinterpret_cast<unsigned char*>(compressedData.data());
                    zs.avail_in = compressedData.size();
                    zs.next_out = reinterpret_cast<unsigned char*>(tmp.data());
                    zs.avail_out = tmp.size();
                    const int r = inflate(&zs, Z_FINISH);
                    const u64 out_n = zs.total_out;
                    inflateEnd(&zs);
                    if (!(r == Z_STREAM_END && out_n >= need)) {
                        ++warn_inflate;
                        std::fprintf(stderr, "pkgx: WARN inflate ret=%d out=%llu need=%llu in %s block %llu\n",
                                     r, (unsigned long long)out_n, (unsigned long long)need,
                                     out_path.c_str(), (unsigned long long)j);
                    }
                }
            } else {
                std::memset(decompressedData.data(), 0, 0x10000);
            }

            size_decompressed += 0x10000;

            if (j < nblocks - 1) {
                inflated.WriteRaw<u8>(decompressedData.data(), decompressedData.size());
            } else {
                // This is to remove the zeros at the end of the file.
                const u64 write_size = decompressedData.size() - (size_decompressed - bsize);
                inflated.WriteRaw<u8>(decompressedData.data(), write_size);
            }
        }
        pkgFile.Close();
        inflated.Close();
    }
}
'''
(d / "pkg.cpp").write_text(c)
print("patched")
