#!/usr/bin/env bash
# Build libcodec2.so with the DATAC1X mode (hfi_modes.c) on Linux.
#
#   ./codec2_patch/build-linux.sh            # clone/update, patch, build, install
#   ./codec2_patch/build-linux.sh --reset    # start from a clean clone (discards clone edits)
#   ./codec2_patch/build-linux.sh --help
#
# The result is copied to <root>/src/libcodec2.so, where modem.py looks for it.
set -euo pipefail

CODEC2_REPO="https://github.com/drowe67/codec2.git"
CODEC2_COMMIT="310777b1c6f1af0bc7c72f5b32f80f6fd9136962"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLONE_DIR="$REPO_ROOT/codec2"
BUILD_DIR="$CLONE_DIR/build"
DEST="$REPO_ROOT/src/libcodec2.so"
PATCH_FILE="$SCRIPT_DIR/CMakeLists.patch"
MODE_FILE="$SCRIPT_DIR/hfi_modes.c"

RESET=0
_dying=0


# output helpers
if [ -t 1 ]; then
    C_INFO=$'\033[1;32m'; C_WARN=$'\033[1;33m'; C_ERR=$'\033[1;31m'; C_OFF=$'\033[0m'
else
    C_INFO=""; C_WARN=""; C_ERR=""; C_OFF=""
fi

info() { printf '%s==>%s %s\n' "$C_INFO" "$C_OFF" "$*"; }
warn() { printf '%s/!\\%s %s\n' "$C_WARN" "$C_OFF" "$*" >&2; }
err()  { printf '%sERROR:%s %s\n' "$C_ERR" "$C_OFF" "$*" >&2; }

die() {
    _dying=1
    err "$*"
    exit 1
}

on_error() {
    [ "$_dying" = 1 ] && return 0
    err "failure at line $1 - build aborted"
}
trap 'on_error "$LINENO"' ERR

usage() {
    cat <<EOF
Usage: $(basename "$0") [--reset] [--help]

Clones codec2 (commit $CODEC2_COMMIT), adds the DATAC1X mode,
builds the shared library and installs it as src/libcodec2.so.

Options:
  --reset   Start from a clean clone: discard modifications and remove
            untracked files under ./codec2 (including build/).
  --help    Show this help.
EOF
}

for arg in "$@"; do
    case "$arg" in
        --reset) RESET=1 ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; die "unknown option: $arg" ;;
    esac
done


# check for needed commands
info "Checking tools"
missing=()
for cmd in git cmake make cc; do
    command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
done
if [ "${#missing[@]}" -gt 0 ]; then
    die "missing tool(s): ${missing[*]}
  Install them, for example: sudo apt install build-essential cmake git"
fi

[ -f "$PATCH_FILE" ] || die "patch not found: $PATCH_FILE"
[ -s "$PATCH_FILE" ] || die "patch is empty: $PATCH_FILE"
[ -f "$MODE_FILE" ]  || die "mode file not found: $MODE_FILE"
[ -s "$MODE_FILE" ]  || die "mode file is empty: $MODE_FILE"
[ -d "$REPO_ROOT/src" ] || die "src directory not found: $REPO_ROOT/src"

# Compare two repository URLs, ignoring a trailing ".git" and "/".
same_repo() {
    local a="${1%.git}" b="${2%.git}"
    a="${a%/}"; b="${b%/}"
    [ "$a" = "$b" ]
}


# clone and checkout codec2
if [ ! -e "$CLONE_DIR" ]; then
    info "Cloning codec2 into $CLONE_DIR"
    git clone "$CODEC2_REPO" "$CLONE_DIR"
elif [ ! -d "$CLONE_DIR/.git" ]; then
    die "$CLONE_DIR exists but is not a git repository.
  Remove or rename it, then try again."
else
    info "Reusing existing clone: $CLONE_DIR"
    origin="$(git -C "$CLONE_DIR" remote get-url origin 2>/dev/null || true)"
    [ -n "$origin" ] || die "the clone has no 'origin' remote; remove $CLONE_DIR"
    same_repo "$origin" "$CODEC2_REPO" || die "unexpected origin in $CLONE_DIR: $origin
  Expected: $CODEC2_REPO - remove the directory and try again."
fi

cd "$CLONE_DIR"

# check that nothing else in the clone has been changed
unexpected_changes() {
    git status --porcelain \
        | grep -vE '^( M|M |MM|\?\?) src/(CMakeLists\.txt|hfi_modes\.c)$' \
        | grep -vE '^\?\? build/$' || true
}

if [ "$RESET" = 1 ]; then
    info "--reset: restoring the clone to a clean state"
    git fetch --quiet origin || die "git fetch failed"
    git -c advice.detachedHead=false checkout -f --detach "$CODEC2_COMMIT" \
        || die "cannot check out $CODEC2_COMMIT"
    git clean -fdq || die "cannot clean the clone"
else
    dirty="$(unexpected_changes)"
    if [ -n "$dirty" ]; then
        printf '%s\n' "$dirty" >&2
        die "the clone at $CLONE_DIR has unexpected changes.
  Commit them, stash them, or rerun with --reset to discard them."
    fi

    head="$(git rev-parse HEAD)"
    if [ "$head" != "$CODEC2_COMMIT" ]; then
        # Only switch commits when nothing (not even the patch) is applied.
        if [ -n "$(git status --porcelain)" ]; then
            die "the clone is at $head instead of $CODEC2_COMMIT, with local changes.
  Rerun with --reset to return to the right commit."
        fi
        info "Switching to commit $CODEC2_COMMIT"
        git fetch --quiet origin || die "git fetch failed"
        git -c advice.detachedHead=false checkout --detach "$CODEC2_COMMIT" \
            || die "cannot check out $CODEC2_COMMIT"
    fi
fi

head="$(git rev-parse HEAD)"
[ "$head" = "$CODEC2_COMMIT" ] || die "HEAD=$head instead of $CODEC2_COMMIT"
info "codec2 commit: $head"


# add the extra c file, and apply the cmake patch
info "Copying hfi_modes.c"
cp "$MODE_FILE" "$CLONE_DIR/src/hfi_modes.c"

if git apply --reverse --check "$PATCH_FILE" >/dev/null 2>&1; then
    info "CMakeLists patch already applied, continuing"
elif git apply --check "$PATCH_FILE" >/dev/null 2>&1; then
    info "Applying CMakeLists.patch"
    git apply "$PATCH_FILE" || die "git apply failed"
else
    die "the patch does not apply (CMakeLists.txt modified?).
  Rerun with --reset to start from a clean clone."
fi

grep -q 'hfi_modes\.c' "$CLONE_DIR/src/CMakeLists.txt" \
    || die "hfi_modes.c is missing from src/CMakeLists.txt after patching"


# build codec2
info "Preparing the build directory"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

info "Configuring CMake (shared library, Release)"
cmake -S "$CLONE_DIR" -B "$BUILD_DIR" \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_BUILD_TYPE=Release \
    || die "CMake configuration failed"

jobs="$(nproc 2>/dev/null || echo 2)"
info "Building the codec2 target (make -j$jobs)"
make -C "$BUILD_DIR" -j"$jobs" codec2 || die "build failed"


# install the new shared lib into src/
candidate="$BUILD_DIR/src/libcodec2.so"
if [ ! -e "$candidate" ]; then
    candidate="$(find "$BUILD_DIR" -name 'libcodec2.so' -print -quit 2>/dev/null || true)"
fi
[ -n "$candidate" ] && [ -e "$candidate" ] || die "libcodec2.so not found in $BUILD_DIR"

info "Installing to $DEST"
cp -Lf "$candidate" "$DEST" || die "cannot copy to $DEST"

[ -s "$DEST" ] || die "$DEST is empty"


# check that symbols hfi_open and hfi_config are actually present
if command -v nm >/dev/null 2>&1; then
    for sym in hfi_open hfi_config; do
        # awk reads all input (no SIGPIPE with pipefail, unlike grep -q).
        nm -D --defined-only "$DEST" 2>/dev/null \
            | awk -v s="$sym" '$NF == s { found = 1 } END { exit !found }' \
            || die "symbol $sym is missing from $DEST (patch not compiled?)"
    done
    info "Symbols hfi_open / hfi_config present"
else
    warn "nm not found: skipping symbol check"
fi

# double check that python / ctypes is happy
if command -v python3 >/dev/null 2>&1; then
    python3 - "$DEST" <<'PY' || die "the library does not load with ctypes"
import ctypes, sys
lib = ctypes.CDLL(sys.argv[1])
assert hasattr(lib, "hfi_open"), "hfi_open missing"
PY
    info "ctypes load: OK"
else
    warn "python3 not found: skipping load test"
fi

info "Done."
printf '    commit  : %s\n    binary  : %s\n    installed: %s\n' \
    "$CODEC2_COMMIT" "$BUILD_DIR/src" "$DEST"
