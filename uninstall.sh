#!/usr/bin/env bash
# Remove everything install.sh added. Your settings and pairing credentials are
# left alone (~/.config/doubletake) — delete that directory yourself if you
# want them gone too.

set -euo pipefail

BIN_DIR="$HOME/.local/bin"
LIBEXEC_DIR="$HOME/.local/libexec/doubletake"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
EXT_DIR="$DATA_DIR/gnome-shell/extensions/doubletake@local"

say() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }

say "Removing the Shell extension"
rm -rf "$EXT_DIR"
if command -v gsettings >/dev/null; then
    python3 - <<'PY' || true
import ast, subprocess
uuid = "doubletake@local"
out = subprocess.run(["gsettings", "get", "org.gnome.shell", "enabled-extensions"],
                     capture_output=True, text=True, check=True).stdout.strip()
current = ast.literal_eval(out) if out.startswith("[") else []
if uuid in current:
    current = [item for item in current if item != uuid]
    subprocess.run(["gsettings", "set", "org.gnome.shell", "enabled-extensions", str(current)],
                   check=True)
PY
fi

say "Removing binaries and the desktop entry"
rm -f "$BIN_DIR/doubletake" "$BIN_DIR/doubletake-gui"
[ -f "$BIN_DIR/doubletake.bak" ] && mv "$BIN_DIR/doubletake.bak" "$BIN_DIR/doubletake"
rm -rf "$LIBEXEC_DIR"
rm -f "$DATA_DIR/applications/doubletake-gui.desktop"
command -v update-desktop-database >/dev/null \
    && update-desktop-database "$DATA_DIR/applications" >/dev/null 2>&1 || true

cat <<'EOF'

Done. Settings and pairing credentials are still in ~/.config/doubletake.
Log out and back in to drop the top bar icon from the running session.
EOF
