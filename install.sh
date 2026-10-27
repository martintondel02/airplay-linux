#!/usr/bin/env bash
# Install Doubletake GNOME: a top bar indicator + desktop GUI for
# https://github.com/omarroth/doubletake, built from source on Fedora.
#
# Everything lands in your home directory:
#   ~/.local/libexec/doubletake/doubletake   the real binary (patched build)
#   ~/.local/bin/doubletake                  wrapper (VA workaround + defaults)
#   ~/.local/bin/doubletake-gui              GTK4 front end
#   ~/.local/share/applications/…            desktop entry
#   ~/.local/share/gnome-shell/extensions/doubletake@local/
#   ~/.config/doubletake/shell.json          shared settings

set -euo pipefail

REPO_URL="https://github.com/omarroth/doubletake"
# Pinned: the upstream commit this patch and build were tested against.
DOUBLETAKE_REF="${DOUBLETAKE_REF:-5e2f1cbe3e1070bcefec8e549c7baf884727bc00}"
GO_VERSION="${GO_VERSION:-1.25.4}"
GO_DIR="$HOME/.local/go-toolchain"

BIN_DIR="$HOME/.local/bin"
LIBEXEC_DIR="$HOME/.local/libexec/doubletake"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/doubletake"
EXT_DIR="$DATA_DIR/gnome-shell/extensions/doubletake@local"

WITH_GUI=1
WITH_EXTENSION=1
SKIP_BUILD=0

say() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
ok() { printf '\033[1;32m  ✓\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

usage() {
    cat <<EOF
Usage: ./install.sh [options]

  --no-gui          Skip the GTK4 desktop app
  --no-extension    Skip the GNOME Shell top bar indicator
  --skip-build      Reuse an existing build in ./.build (offline re-install)
  -h, --help        Show this help

Environment:
  DOUBLETAKE_REF    Upstream commit or tag to build (default: $DOUBLETAKE_REF)
  GO_VERSION        Go toolchain version to download if none is installed
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --no-gui) WITH_GUI=0 ;;
        --no-extension) WITH_EXTENSION=0 ;;
        --skip-build) SKIP_BUILD=1 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown option: $1 (try --help)" ;;
    esac
    shift
done

here="$(cd "$(dirname "$0")" && pwd)"

# ---------------------------------------------------------------- sanity check
if ! grep -qi '^ID=fedora' /etc/os-release 2>/dev/null; then
    warn "this script targets Fedora; continuing anyway"
fi

command -v gst-inspect-1.0 >/dev/null || die "GStreamer not found. Install it with:
  sudo dnf install gstreamer1-plugins-base gstreamer1-plugins-good \\
                   gstreamer1-plugins-bad-free gstreamer1-plugins-ugly-free \\
                   gstreamer1-plugin-libav gstreamer1-plugin-openh264"

missing=""
for element in pipewiresrc openh264enc avenc_alac; do
    gst-inspect-1.0 "$element" >/dev/null 2>&1 || missing="$missing $element"
done
if [ -n "$missing" ]; then
    die "missing GStreamer elements:$missing
Install them with:
  sudo dnf install gstreamer1-plugins-base gstreamer1-plugins-good \\
                   gstreamer1-plugins-bad-free gstreamer1-plugins-ugly-free \\
                   gstreamer1-plugin-libav gstreamer1-plugin-openh264"
fi
ok "GStreamer elements present"

command -v pactl >/dev/null || die "pactl not found: sudo dnf install pulseaudio-utils"
ok "pactl present"

if [ "$SKIP_BUILD" -eq 0 ]; then
    command -v curl >/dev/null || die "curl is required"
    command -v tar >/dev/null || die "tar is required"
fi

# ------------------------------------------------------------------------- go
if [ "$SKIP_BUILD" -eq 0 ]; then
    if ! command -v go >/dev/null; then
        say "Go not found — downloading Go $GO_VERSION to $GO_DIR"
        mkdir -p "$GO_DIR"
        tmp="$(mktemp -d)"
        curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -o "$tmp/go.tar.gz"
        rm -rf "$GO_DIR/go"
        tar -C "$GO_DIR" -xzf "$tmp/go.tar.gz"
        rm -rf "$tmp"
        export PATH="$GO_DIR/go/bin:$PATH"
        [ -x "$GO_DIR/go/bin/go" ] || die "Go download failed"
        ok "Go installed in $GO_DIR (only needed for building)"
    else
        ok "Go $(go version | awk '{print $3}')"
    fi
fi

# ---------------------------------------------------------------------- build
if [ "$SKIP_BUILD" -eq 0 ]; then
    say "Fetching doubletake @ ${DOUBLETAKE_REF:0:8}"
    build_dir="$here/.build"
    rm -rf "$build_dir"
    mkdir -p "$build_dir"
    curl -fsSL "$REPO_URL/archive/$DOUBLETAKE_REF.tar.gz" -o "$build_dir/src.tar.gz"
    tar -C "$build_dir" -xzf "$build_dir/src.tar.gz"
    src="$(find "$build_dir" -maxdepth 1 -type d -name 'doubletake-*' | head -n1)"
    [ -n "$src" ] || die "could not unpack the doubletake source"

    say "Applying the VA-scaling opt-out patch"
    ( cd "$src" && git apply --whitespace=nowarn "$here/patches/0001-optional-va-scaling-opt-out.patch" ) \
        || die "patch did not apply cleanly — upstream may have moved. Try DOUBLETAKE_REF=<other commit>"
    ok "patch applied"

    say "Building (this takes a minute)"
    ( cd "$src" && GOFLAGS=-mod=mod CGO_ENABLED=0 \
        go build -trimpath -ldflags="-s -w" -o "$build_dir/doubletake" ./cmd/doubletake )
    [ -x "$build_dir/doubletake" ] || die "build produced no binary"
    ok "built $("$build_dir/doubletake" -h 2>&1 | head -n0; echo doubletake)"
fi

[ -x "$here/.build/doubletake" ] || die "no build found; run without --skip-build"

# -------------------------------------------------------------------- install
say "Installing binaries into $HOME/.local"
mkdir -p "$BIN_DIR" "$LIBEXEC_DIR" "$CONFIG_DIR"
install -m 755 "$here/.build/doubletake" "$LIBEXEC_DIR/doubletake"

cat > "$BIN_DIR/doubletake" <<'WRAPPER'
#!/bin/sh
# Wrapper installed by "Doubletake GNOME" — see the README.
#
# 1. Capture path: some Mesa/GStreamer combinations (notably AMD radeonsi with
#    GStreamer 1.28) start the VA postprocessor pipeline and then lose the
#    GStreamer child after a couple of seconds. The system-memory plan avoids
#    it; with a software encoder it costs nothing extra. Set
#    DOUBLETAKE_VA_SCALING=1 to use the VA path anyway.
# 2. Bitrate: the built-in auto formula picks ~4.1 Mbps for 1080p30, which is
#    conservative for desktop text. Default to 12 Mbps (the tool's ceiling)
#    unless -bitrate is given. Override with DOUBLETAKE_BITRATE.
DOUBLETAKE_DISABLE_VA_SCALING="${DOUBLETAKE_DISABLE_VA_SCALING-1}"
export DOUBLETAKE_DISABLE_VA_SCALING

real="$HOME/.local/libexec/doubletake/doubletake"

bitrate="${DOUBLETAKE_BITRATE:-12000}"
for arg in "$@"; do
    case "$arg" in
        -bitrate|--bitrate|-bitrate=*|--bitrate=*) bitrate="" ;;
    esac
done

if [ -n "$bitrate" ]; then
    exec "$real" "$@" -bitrate "$bitrate"
fi
exec "$real" "$@"
WRAPPER
chmod 755 "$BIN_DIR/doubletake"
ok "$BIN_DIR/doubletake (wrapper) + $LIBEXEC_DIR/doubletake"

if [ "$WITH_GUI" -eq 1 ]; then
    install -m 755 "$here/gui/doubletake-gui" "$BIN_DIR/doubletake-gui"
    mkdir -p "$DATA_DIR/applications"
    sed "s|@GUI@|$BIN_DIR/doubletake-gui|g" "$here/desktop/doubletake-gui.desktop.in" \
        > "$DATA_DIR/applications/doubletake-gui.desktop"
    command -v update-desktop-database >/dev/null \
        && update-desktop-database "$DATA_DIR/applications" >/dev/null 2>&1 || true
    ok "$BIN_DIR/doubletake-gui + desktop entry"
fi

if [ "$WITH_EXTENSION" -eq 1 ]; then
    mkdir -p "$EXT_DIR"
    install -m 644 "$here/extension/metadata.json" "$EXT_DIR/metadata.json"
    install -m 644 "$here/extension/extension.js" "$EXT_DIR/extension.js"
    ok "extension files in $EXT_DIR"

    # Pre-enable it; the Shell only scans for new extensions at session start.
    if command -v gsettings >/dev/null; then
        python3 - "$EXT_DIR" <<'PY' || warn "could not add the extension to enabled-extensions"
import ast, subprocess, sys
uuid = "doubletake@local"
out = subprocess.run(["gsettings", "get", "org.gnome.shell", "enabled-extensions"],
                     capture_output=True, text=True, check=True).stdout.strip()
current = ast.literal_eval(out) if out.startswith("[") else []
if uuid not in current:
    current.append(uuid)
    subprocess.run(["gsettings", "set", "org.gnome.shell", "enabled-extensions", str(current)],
                   check=True)
PY
        ok "extension pre-enabled (appears after the next login)"
    fi
fi

# Shared settings, only if the user has none yet.
if [ ! -f "$CONFIG_DIR/shell.json" ]; then
    cat > "$CONFIG_DIR/shell.json" <<'JSON'
{
  "target": "192.168.1.169",
  "name": "",
  "bitrate": 12000,
  "fps": 30
}
JSON
    ok "default settings in $CONFIG_DIR/shell.json"
fi

cat <<EOF

$(printf '\033[1;32mDone.\033[0m')

Next steps
  1. Log out and back in once — GNOME only scans for new extensions at login.
  2. Find your Apple TV:   avahi-browse -rtp _airplay._tcp | grep '='
  3. Pair (one time):      doubletake -target <ip> -pair
     …or use the top bar menu / the "Doubletake" app and enter the PIN.

Try it now without logging out:
  doubletake -target <ip>
  doubletake-gui &

Docs: README.md
EOF
