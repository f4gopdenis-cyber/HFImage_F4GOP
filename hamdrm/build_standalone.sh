#!/bin/sh
# HFImage F4GOP - builds the standalone HamDRM modem library (no Qt, no FFTW)
#   ./build_standalone.sh linux     -> libhamdrm.so
#   ./build_standalone.sh windows   -> hamdrm.dll (MinGW-w64, static runtime)
set -e
cd "$(dirname "$0")"
TARGET=${1:-linux}
OUT=${2:-.}
SRC="$(find tx rx support -name '*.cpp') api/hamdrm.cpp capi/hamdrm_c.cpp shim/minifft.cpp"
INC="-Ishim -Istubs -Iapi -Icapi -Isupport -Irx -I. -Itx -Itx/common -Itx/common/util -Itx/common/matlib -Itx/common/datadecoding -Itx/common/tables"
FLAGS="-std=gnu++17 -O2 -w -DHAMDRM_STANDALONE"
if [ "$TARGET" = windows ]; then
  CXX=${CXX:-x86_64-w64-mingw32-g++-posix}
  $CXX $FLAGS $INC -shared -o "$OUT/hamdrm.dll" $SRC \
    -static -static-libgcc -static-libstdc++ -Wl,--exclude-all-symbols -s
  echo "built $OUT/hamdrm.dll"
else
  CXX=${CXX:-g++}
  $CXX $FLAGS -fPIC -fvisibility=hidden $INC -shared -o "$OUT/libhamdrm.so" $SRC -static-libstdc++ -static-libgcc -s
  echo "built $OUT/libhamdrm.so"
fi
