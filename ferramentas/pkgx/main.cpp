// pkgx: command-line PS4 PKG extractor built from shadPS4 v.0.6.0's own PKG/PFS code
// (src/core/file_format/pkg.cpp, src/core/crypto). Does what the Qt GUI "Install" does:
// PKG::Extract (sce_sys entries incl. decrypted NP entries + PFS directory tree), then
// PKG::ExtractFiles for every file index, in parallel.
//
//   pkgx [-j N] [-l] <file.pkg> <outdir>
//     -l   only list the files (path and size), extract nothing but sce_sys
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <string>
#include <thread>
#include <vector>
#include "common/io_file.h"
#include "core/file_format/pkg.h"

int main(int argc, char** argv) {
    unsigned jobs = std::max(1u, std::thread::hardware_concurrency());
    bool list_only = false;
    std::vector<std::string> args;
    for (int i = 1; i < argc; i++) {
        if (!std::strcmp(argv[i], "-j") && i + 1 < argc)
            jobs = std::max(1, std::atoi(argv[++i]));
        else if (!std::strcmp(argv[i], "-l"))
            list_only = true;
        else
            args.emplace_back(argv[i]);
    }
    if (args.size() != 2) {
        std::fprintf(stderr, "usage: pkgx [-j N] [-l] <file.pkg> <outdir>\n");
        return 2;
    }
    const std::filesystem::path pkg_path = args[0];
    const std::filesystem::path out = std::filesystem::absolute(args[1]);
    std::filesystem::create_directories(out);

    PKG pkg;
    std::string fail;
    if (!pkg.Open(pkg_path, fail)) {
        std::fprintf(stderr, "pkgx: not a valid PKG: %s %s\n", pkg_path.c_str(), fail.c_str());
        return 1;
    }
    const auto hdr = pkg.GetPkgHeader();
    std::printf("pkg: %s\ntitle: %.*s  flags: %s  size: %llu\n", pkg_path.c_str(),
                (int)pkg.GetTitleID().size(), pkg.GetTitleID().data(), pkg.GetPkgFlags().c_str(),
                (unsigned long long)pkg.GetPkgSize());
    (void)hdr;

    if (!pkg.Extract(pkg_path, out, fail)) {
        std::fprintf(stderr, "pkgx: Extract failed: %s\n", fail.c_str());
        return 1;
    }
    const int n = (int)pkg.GetNumberOfFiles();
    int nfiles = 0;
    unsigned long long total = 0;
    for (int i = 0; i < n; i++)
        if (pkg.GetFileType(i) == PFS_FILE) {
            nfiles++;
            total += pkg.GetFileSize(i);
            if (list_only)
                std::printf("%12llu %s\n", (unsigned long long)pkg.GetFileSize(i),
                            pkg.GetFilePath(i).lexically_relative(out).c_str());
        }
    std::printf("entries: %d  files: %d  bytes: %llu\n", n, nfiles, total);
    if (list_only)
        return 0;

    std::atomic<int> next{0}, done{0};
    std::atomic<unsigned long long> bytes{0};
    std::vector<std::thread> pool;
    for (unsigned t = 0; t < jobs; t++)
        pool.emplace_back([&] {
            for (int i; (i = next.fetch_add(1)) < n;) {
                pkg.ExtractFiles(i);
                if (pkg.GetFileType(i) == PFS_FILE) {
                    bytes += pkg.GetFileSize(i);
                    const int d = ++done;
                    if (true)  // cada arquivo: o instalador do Deck mostra o progresso (poucos arquivos grandes)
                        std::fprintf(stderr, "  %d/%d files, %.1f/%.1f GiB\n", d, nfiles,
                                     bytes / 1073741824.0, total / 1073741824.0);
                }
            }
        });
    for (auto& th : pool)
        th.join();

    // Verify sizes on disk.
    int bad_size = 0;
    for (int i = 0; i < n; i++)
        if (pkg.GetFileType(i) == PFS_FILE) {
            std::error_code ec;
            const auto sz = std::filesystem::file_size(pkg.GetFilePath(i), ec);
            if (ec || sz != pkg.GetFileSize(i)) {
                bad_size++;
                std::fprintf(stderr, "pkgx: size mismatch %s\n", pkg.GetFilePath(i).c_str());
            }
        }
    const unsigned long long io = Common::FS::IOFile::errors, sr = PKG::warn_short_read,
                             inf = PKG::warn_inflate, blk = PKG::warn_block;
    std::printf("done: %d files, %llu bytes -> %s\n", nfiles, total, out.c_str());
    std::printf("checks: io_errors=%llu short_reads=%llu inflate_warnings=%llu odd_blocks=%llu "
                "size_mismatches=%d\n",
                io, sr, inf, blk, bad_size);
    return (io || sr || inf || bad_size) ? 3 : 0;
}
