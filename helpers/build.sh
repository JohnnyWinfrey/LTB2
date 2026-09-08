#!/usr/bin/env bash
# Build th260_helper_ultra. Run from anywhere; paths are resolved relative to
# this script.
#
#   ./helpers/build.sh win     cross-compile the Windows .exe (needs mingw-w64
#                              and the PicoQuant SDK headers in helpers/include/)
#   ./helpers/build.sh stub    native binary linked against th260_stub.cpp, for
#                              driving the line protocol locally
#   ./helpers/build.sh         both
#
# The repo has no other build script -- the helper EXEs are committed binaries.
# Commit the rebuilt .exe after running the `win` target.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/th260_helper_ultra.cpp"
STUB_OUT="${STUB_OUT:-/tmp/th260_helper_stub}"

build_win() {
    local CXX=x86_64-w64-mingw32-g++
    if ! command -v "$CXX" >/dev/null; then
        echo "error: $CXX not found -- brew install mingw-w64" >&2
        exit 1
    fi
    if [ ! -f "$HERE/include/th260lib.h" ] && [ -z "${TH260_ALLOW_FALLBACK_DECLS:-}" ]; then
        echo "error: PicoQuant SDK headers missing." >&2
        echo "       Copy th260lib.h, th260defin.h and errorcodes.h from the" >&2
        echo "       TH260 SDK on the instrument PC into helpers/include/." >&2
        echo "       Or set TH260_ALLOW_FALLBACK_DECLS=1 to build against the" >&2
        echo "       declarations in th260_compat.h -- these match the published" >&2
        echo "       API and x64 has one calling convention, but they are not" >&2
        echo "       verified against your SDK version." >&2
        exit 1
    fi
    # MinGW's ld links a PE DLL directly, so no import library is needed.
    # -static pulls in libwinpthread too: the instrument PC has no mingw
    # runtime and no internet, so the .exe has to be self-contained.
    "$CXX" -O2 -std=c++17 -Wall -static -s \
        -I"$HERE/include" "$SRC" "$HERE/th260lib64.dll" \
        -o "$HERE/th260_helper_ultra.exe"
    echo "built $HERE/th260_helper_ultra.exe"
    file "$HERE/th260_helper_ultra.exe" 2>/dev/null || true
}

build_stub() {
    local CXX="${CXX:-c++}"
    "$CXX" -O0 -g -std=c++17 -Wall \
        -I"$HERE/include" "$SRC" "$HERE/th260_stub.cpp" \
        -o "$STUB_OUT"
    echo "built $STUB_OUT"
}

case "${1:-all}" in
    win)  build_win ;;
    stub) build_stub ;;
    all)  build_stub; build_win ;;
    *)    echo "usage: $0 [win|stub|all]" >&2; exit 2 ;;
esac
