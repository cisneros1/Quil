#!/usr/bin/env bash
# Remove every Quil package installed by ./install.sh.
# Switch to another Global Theme first if Quil is currently applied.
set -euo pipefail
cd "$(dirname "$0")"

DEST="${XDG_DATA_HOME:-$HOME/.local/share}"
[[ -f build/manifest.txt ]] || python3 tools/build.py

UNIT="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/quil-badges.service"
if [[ -f "$UNIT" ]]; then
  systemctl --user disable --now quil-badges.service >/dev/null 2>&1 || true
  rm -f "$UNIT"
  systemctl --user daemon-reload 2>/dev/null || true
  echo "removed $UNIT"
fi

DARKLYRC="${XDG_CONFIG_HOME:-$HOME/.config}/kdedefaults/darklyrc"
if [[ -f "$DARKLYRC" ]] && cmp -s "$DARKLYRC" src/kdedefaults/darklyrc; then
  rm -f "$DARKLYRC"
  echo "removed $DARKLYRC"
fi

KWINRC="${XDG_CONFIG_HOME:-$HOME/.config}/kdedefaults/kwinrc"
if [[ -f "$KWINRC" ]]; then
  kwriteconfig6 --file "$KWINRC" --group Effect-blur --key BlurStrength --delete
  qdbus6 org.kde.KWin /Effects org.kde.kwin.Effects.reconfigureEffect blur >/dev/null 2>&1 || true
  echo "removed Quil's blur strength from $KWINRC"
fi

KDEDEFAULTS="${XDG_CONFIG_HOME:-$HOME/.config}/kdedefaults"
if [[ -f "$KWINRC" ]] && [[ "$(kreadconfig6 --file "$KWINRC" --group Plugins --key better_blur_dxEnabled)" == true ]]; then
  # back to KWin's own blur; Better Blur DX itself stays installed
  kwriteconfig6 --file "$KWINRC" --group Plugins --key blurEnabled --delete
  kwriteconfig6 --file "$KWINRC" --group Plugins --key better_blur_dxEnabled --delete
  kwriteconfig6 --file "$KWINRC" --group Effect-better-blur-dx --key WindowClasses --delete
  qdbus6 org.kde.KWin /Effects org.kde.kwin.Effects.unloadEffect better_blur_dx >/dev/null 2>&1 || true
  qdbus6 org.kde.KWin /Effects org.kde.kwin.Effects.loadEffect blur >/dev/null 2>&1 || true
  echo "switched KWin back to its own blur effect"
fi

RULES="${XDG_CONFIG_HOME:-$HOME/.config}/kwinrulesrc"
RULE_ID=quil-translucent-system-apps
if [[ -f "$RULES" ]] && grep -qx "\[$RULE_ID\]" "$RULES"; then
  python3 -I - "$RULES" "$RULE_ID" <<'PY'
import configparser, sys
path, rule = sys.argv[1:]
cp = configparser.RawConfigParser(strict=False, interpolation=None)
cp.optionxform = str
cp.read(path)
cp.remove_section(rule)
for key in ("Order", "rules"):
    if cp.has_option("General", key):
        cp.set("General", key, ",".join(r for r in cp.get("General", key).split(",") if r and r != rule))
if cp.has_option("General", "count"):
    cp.set("General", "count", str(len([r for r in cp.get("General", "rules", fallback=cp.get("General", "Order", fallback="")).split(",") if r])))
with open(path, "w") as f:
    cp.write(f, space_around_delimiters=False)
PY
  qdbus6 org.kde.KWin /KWin reconfigure >/dev/null 2>&1 || true
  echo "removed window rule $RULE_ID"
fi

if [[ "$(kreadconfig6 --file "$KDEDEFAULTS/konsolerc" --group "Desktop Entry" --key DefaultProfile)" == Quil-*.profile ]]; then
  kwriteconfig6 --file "$KDEDEFAULTS/konsolerc" --group "Desktop Entry" --key DefaultProfile --delete
  echo "reset Konsole's default profile"
fi

for rc in katerc kwriterc; do
  if [[ "$(kreadconfig6 --file "$KDEDEFAULTS/$rc" --group "KTextEditor Renderer" --key "Color Theme")" == Quil\ * ]]; then
    kwriteconfig6 --file "$KDEDEFAULTS/$rc" --group "KTextEditor Renderer" --key "Color Theme" --delete
    kwriteconfig6 --file "$KDEDEFAULTS/$rc" --group "KTextEditor Renderer" --key "Auto Color Theme Selection" --delete
    echo "reset the syntax colors default in $rc"
  fi
done

if [[ -d /usr/local/share/plasma/desktoptheme/Quil-Dark || -d /usr/local/share/icons/Quil-Dark ]]; then
  echo "note: the login screen still uses Quil; undo that with: tools/login_screen.py --remove (needs sudo)"
fi

while IFS= read -r rel; do
  [[ -z "$rel" ]] && continue
  if [[ -e "$DEST/$rel" || -L "$DEST/$rel" ]]; then
    rm -rf "${DEST:?}/$rel"
    echo "removed $DEST/$rel"
  fi
done < build/manifest.txt
