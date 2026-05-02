#!/usr/bin/env bash
# Install JarvisX as a desktop application — Linux only, run as user.
#
# What this does:
#   1. Marks launch.sh as executable
#   2. Copies the icon to ~/.local/share/icons/hicolor/.../apps/
#   3. Renders JarvisX.desktop.template with absolute paths and
#      installs it at ~/.local/share/applications/JarvisX.desktop
#   4. Refreshes the icon + desktop database so the entry shows up
#      immediately without logout
#
# Idempotent — re-running just refreshes the entry. Useful after
# moving the repo to a different path.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JARVISX_DIR="$(dirname "$SCRIPT_DIR")"
LAUNCH_SH="$JARVISX_DIR/scripts/launch.sh"
ICON_SVG="$JARVISX_DIR/assets/icon.svg"
ICON_PNG_512="$JARVISX_DIR/assets/icon.png"
TEMPLATE="$SCRIPT_DIR/JarvisX.desktop.template"

if [[ ! -f "$LAUNCH_SH" ]] || [[ ! -f "$ICON_SVG" ]] || [[ ! -f "$TEMPLATE" ]]; then
  echo "[install-desktop] missing required files — run from a checked-out repo." >&2
  exit 1
fi

chmod +x "$LAUNCH_SH"

# Icon: install both SVG (scalable) and a 512×512 PNG fallback for
# desktop environments that don't render SVG in the taskbar.
ICON_DIR_SVG="$HOME/.local/share/icons/hicolor/scalable/apps"
ICON_DIR_PNG="$HOME/.local/share/icons/hicolor/512x512/apps"
mkdir -p "$ICON_DIR_SVG" "$ICON_DIR_PNG"
cp -f "$ICON_SVG" "$ICON_DIR_SVG/jarvisx.svg"
if [[ -f "$ICON_PNG_512" ]]; then
  cp -f "$ICON_PNG_512" "$ICON_DIR_PNG/jarvisx.png"
fi

# Render the desktop entry with absolute paths
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
DESKTOP_FILE="$APPS_DIR/JarvisX.desktop"
sed \
  -e "s|__JARVISX_LAUNCH__|$LAUNCH_SH|g" \
  -e "s|__JARVISX_ICON__|jarvisx|g" \
  "$TEMPLATE" > "$DESKTOP_FILE"
chmod +x "$DESKTOP_FILE"

# Refresh caches so the entry appears immediately. These commands
# vary by desktop env; we silence failures.
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true

echo "[install-desktop] installed."
echo "  Launcher: $LAUNCH_SH"
echo "  Icon:     $ICON_DIR_SVG/jarvisx.svg"
echo "  Entry:    $DESKTOP_FILE"
echo
echo "JarvisX should now appear in your application menu."
echo "If not, log out + back in to refresh the desktop database."
