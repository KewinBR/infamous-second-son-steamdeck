// Minimal stdio replacement for shadPS4's Common::FS::IOFile (only what pkg.cpp uses).
// Same semantics as the original for the calls used: Read(container) reads data.size()
// elements, Read(object) reads sizeof(object), ReadRaw/WriteRaw take an element count.
#pragma once

#include <atomic>
#include <cstdio>
#include <filesystem>
#include <span>
#include <type_traits>
#include "common/types.h"

namespace Common::FS {

enum class FileAccessMode { Read = 1, Write = 2 };
enum class SeekOrigin { SetOrigin, CurrentPosition, End };

template <typename T>
concept IsContiguousContainer = requires(T t) {
    t.data();
    t.size();
};

class IOFile {
public:
    IOFile() = default;
    IOFile(const std::filesystem::path& path, FileAccessMode mode) {
        Open(path, mode);
    }
    ~IOFile() {
        Close();
    }
    IOFile(const IOFile&) = delete;
    IOFile& operator=(const IOFile&) = delete;

    void Open(const std::filesystem::path& path, FileAccessMode mode) {
        Close();
        f = std::fopen(path.c_str(), mode == FileAccessMode::Write ? "wb" : "rb");
        if (f && mode == FileAccessMode::Read)
            std::setvbuf(f, nullptr, _IOFBF, 1 << 20);
        if (!f && mode == FileAccessMode::Write)
            std::fprintf(stderr, "pkgx: ERROR cannot create %s\n", path.c_str());
        if (!f)
            ++errors;
    }
    bool IsOpen() const {
        return f != nullptr;
    }
    void Close() {
        if (f) {
            if (std::fclose(f) != 0)
                ++errors;
            f = nullptr;
        }
    }
    u64 GetSize() const {
        if (!f)
            return 0;
        const auto pos = ftello(f);
        fseeko(f, 0, SEEK_END);
        const auto size = ftello(f);
        fseeko(f, pos, SEEK_SET);
        return static_cast<u64>(size);
    }
    bool Seek(s64 offset, SeekOrigin origin = SeekOrigin::SetOrigin) const {
        if (!f)
            return false;
        const int whence = origin == SeekOrigin::SetOrigin       ? SEEK_SET
                           : origin == SeekOrigin::CurrentPosition ? SEEK_CUR
                                                                   : SEEK_END;
        return fseeko(f, offset, whence) == 0;
    }
    s64 Tell() const {
        return f ? ftello(f) : -1;
    }

    template <typename T>
    size_t ReadRaw(void* data, size_t count) const {
        return f ? std::fread(data, sizeof(T), count, f) : 0;
    }
    template <typename T>
    size_t WriteRaw(const void* data, size_t count) const {
        if (!f)
            return 0;
        const size_t n = std::fwrite(data, sizeof(T), count, f);
        if (n != count)
            ++errors;
        return n;
    }
    template <typename T>
    size_t Read(T& data) const {
        if constexpr (IsContiguousContainer<T>) {
            using V = std::remove_cvref_t<decltype(*data.data())>;
            return ReadRaw<V>(data.data(), data.size());
        } else {
            return ReadRaw<u8>(&data, sizeof(T)) == sizeof(T) ? 1 : 0;
        }
    }
    template <typename T>
    size_t Write(const T& data) const {
        if constexpr (IsContiguousContainer<T>) {
            using V = std::remove_cvref_t<decltype(*data.data())>;
            return WriteRaw<V>(data.data(), data.size());
        } else {
            return WriteRaw<u8>(&data, sizeof(T)) == sizeof(T) ? 1 : 0;
        }
    }

    // Global I/O error counter (write failures, open failures, close failures).
    static inline std::atomic<u64> errors{0};

private:
    FILE* f = nullptr;
};

} // namespace Common::FS
