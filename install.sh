#!/usr/bin/env bash
# Build Quil and install it for the current user (~/.local/share).
#   ./install.sh                 build + install both variants
#   ./install.sh --apply dark    ...then switch to Quil Dark (or: light)
#   ./install.sh --apply dark --reset-layout   ...also apply Quil's panel layout
#   ./install.sh --apply dark --login          ...also theme the login screen (needs sudo)
set -euo pipefail
cd "$(dirname "$0")"

DEST="${XDG_DATA_HOME:-$HOME/.local/share}"
BLUR_STRENGTH=2   # KWin blur, 1 (nearly clear) to 15; see below
# Apps (Wayland app ids) made translucent by a window rule; see below.
# org.kde.plasmashell is Plasma's own settings windows (Desktop Folder
# Settings, widget settings); its panels and popups are "plasmashell".
TRANSLUCENT_APPS=(systemsettings org.kde.kinfocenter org.kde.discover org.kde.plasmashell)
RULE_ID=quil-translucent-system-apps
APP_OPACITY=90   # their opacity in percent; lower is more see-through
APPLY=""
RESET_LAYOUT=0
LOGIN=0

usage() { sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY="${2:-}"; shift 2 ;;
    --reset-layout) RESET_LAYOUT=1; shift ;;
    --login) LOGIN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

# Colloid icons, Inter and JetBrains Mono, if they aren't installed yet.
bash tools/fetch_deps.sh

python3 tools/build.py

while IFS= read -r rel; do
  [[ -z "$rel" ]] && continue
  rm -rf "${DEST:?}/$rel"
  mkdir -p "$(dirname "$DEST/$rel")"
  cp -r "build/share/$rel" "$DEST/$rel"
  echo "installed $DEST/$rel"
done < build/manifest.txt

# Darkly app style (if installed): Quil's menu settings, as defaults that
# Darkly's own settings override.
KDEDEFAULTS="${XDG_CONFIG_HOME:-$HOME/.config}/kdedefaults"
if grep -qx 'widgetStyle=Darkly' build/share/plasma/look-and-feel/*/contents/defaults; then
  mkdir -p "$KDEDEFAULTS"
  cp src/kdedefaults/darklyrc "$KDEDEFAULTS/darklyrc"
  echo "installed $KDEDEFAULTS/darklyrc"
else
  echo "note: Darkly isn't installed, so apps keep Breeze menus (paru -S darkly-bin, then re-run ./install.sh)"
fi

# Lighter KWin blur, so the wallpaper shows through the glass dock (KWin's
# default smears it into one flat color). Written as a default, so the
# strength set in System Settings > Desktop Effects > Blur still wins.
# Global themes can't set this themselves.
kwriteconfig6 --file "$KDEDEFAULTS/kwinrc" --group Effect-blur --key BlurStrength "$BLUR_STRENGTH"
qdbus6 org.kde.KWin /Effects org.kde.kwin.Effects.reconfigureEffect blur >/dev/null 2>&1 || true

# Translucent System Settings, Info Center and Discover. They paint their own
# solid backgrounds, so this takes a window rule (85% opacity) plus the Better
# Blur DX KWin effect, which can blur behind any window by class. Only set up
# when Better Blur DX is installed and built for the running KWin
# (paru -S kwin-effects-better-blur-dx). A build for another KWin version
# won't load, and with KWin's own blur switched off Plasma drops the glass
# dock for its solid fallback, so then keep KWin's blur.
BBDX=/usr/lib/qt6/plugins/kwin/effects/plugins/better_blur_dx.so
better_blur_dx_usable() {
  [[ -f "$BBDX" ]] || return 1
  local kwin
  kwin="$(kwin_wayland --version 2>/dev/null | awk '{print $2}')"
  [[ -z "$kwin" ]] || grep -aq "org.kde.kwin.EffectPluginFactory$kwin\b" "$BBDX"
}
kw() { kwriteconfig6 --file "$KDEDEFAULTS/kwinrc" --group "$1" --key "$2" "$3"; }
if better_blur_dx_usable; then
  # Better Blur DX replaces KWin's blur, with the same look as above.
  kw Plugins blurEnabled false
  kw Plugins better_blur_dxEnabled true
  kw Effect-better-blur-dx BlurStrength "$BLUR_STRENGTH"
  kw Effect-better-blur-dx NoiseStrength 0
  kw Effect-better-blur-dx Saturation 100
  kw Effect-better-blur-dx BlurDecorations true   # title bars too
  kw Effect-better-blur-dx BlurMatching true
  kw Effect-better-blur-dx WindowClasses "$(printf '%s\n' "${TRANSLUCENT_APPS[@]}")"
  # The window rule goes in your own kwinrulesrc (KWin keeps one list of rules).
  RULES="${XDG_CONFIG_HOME:-$HOME/.config}/kwinrulesrc"
  kr() { kwriteconfig6 --file "$RULES" --group "$RULE_ID" --key "$1" "$2"; }
  kr Description "Quil: translucent system apps"
  kr wmclass "^($(IFS='|'; echo "${TRANSLUCENT_APPS[*]//./\\.}"))\$"
  kr wmclassmatch 3            # regular expression
  kr types 33                  # normal windows and dialogs only
  kr opacityactive "$APP_OPACITY"
  kr opacityactiverule 2       # force
  kr opacityinactive "$APP_OPACITY"
  kr opacityinactiverule 2
  order="$(kreadconfig6 --file "$RULES" --group General --key Order)"
  [[ -z "$order" ]] && order="$(kreadconfig6 --file "$RULES" --group General --key rules)"
  if [[ ",$order," != *",$RULE_ID,"* ]]; then
    order="${order:+$order,}$RULE_ID"
    kwriteconfig6 --file "$RULES" --group General --key Order "$order"
    kwriteconfig6 --file "$RULES" --group General --key rules "$order"
    kwriteconfig6 --file "$RULES" --group General --key count "$(tr ',' '\n' <<<"$order" | grep -c .)"
  fi
  qdbus6 org.kde.KWin /Effects org.kde.kwin.Effects.unloadEffect blur >/dev/null 2>&1 || true
  qdbus6 org.kde.KWin /Effects org.kde.kwin.Effects.loadEffect better_blur_dx >/dev/null 2>&1 || true
  qdbus6 org.kde.KWin /Effects org.kde.kwin.Effects.reconfigureEffect better_blur_dx >/dev/null 2>&1 || true
  qdbus6 org.kde.KWin /KWin reconfigure >/dev/null 2>&1 || true
  echo "set up translucent ${TRANSLUCENT_APPS[*]} (Better Blur DX)"
else
  # Undo an earlier run that switched to Better Blur DX.
  kw Plugins blurEnabled true
  kw Plugins better_blur_dxEnabled false
  qdbus6 org.kde.KWin /Effects org.kde.kwin.Effects.loadEffect blur >/dev/null 2>&1 || true
  qdbus6 org.kde.KWin /KWin reconfigure >/dev/null 2>&1 || true
  if [[ -f "$BBDX" ]]; then
    echo "note: Better Blur DX was built for a different KWin version, so it's skipped and System Settings stays solid (rebuild it: paru -S kwin-effects-better-blur-dx, then re-run ./install.sh)"
  else
    echo "note: Better Blur DX isn't installed, so System Settings stays solid (paru -S kwin-effects-better-blur-dx, then re-run ./install.sh)"
  fi
fi

# Konsole: Quil's translucent profile as the default, for the applied variant.
slug="$(python3 -c 'import json,sys; p=json.load(open("palette.json")); print(p["meta"]["name"] + "-" + p["variants"][sys.argv[1]]["label"])' "${APPLY:-dark}")"
kwriteconfig6 --file "$KDEDEFAULTS/konsolerc" --group "Desktop Entry" --key DefaultProfile "$slug.profile"

# Kate and KWrite: Quil's syntax colors for the applied variant. Also a
# default, so a theme picked in the editor's own settings still wins.
theme="${slug/-/ }"   # "Quil-Dark" -> "Quil Dark", the name inside the .theme file
for rc in katerc kwriterc; do
  kwriteconfig6 --file "$KDEDEFAULTS/$rc" --group "KTextEditor Renderer" --key "Color Theme" "$theme"
  kwriteconfig6 --file "$KDEDEFAULTS/$rc" --group "KTextEditor Renderer" --key "Auto Color Theme Selection" false
done

# Rounded copies of the dock's app icons, inside the Quil icon themes.
python3 tools/round_icons.py

# Badge relay for Quil Dock (unread counts), as a systemd user service.
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$UNIT_DIR"
cat > "$UNIT_DIR/quil-badges.service" <<UNIT
[Unit]
Description=Quil Dock unread badges (Unity LauncherEntry relay)
PartOf=graphical-session.target
After=graphical-session.target

[Service]
Type=dbus
BusName=com.github.cisneros1.Quil.Badges
ExecStart=/usr/bin/python3 -I "$DEST/quil/quil-badges.py"
Restart=on-failure

[Install]
WantedBy=graphical-session.target
UNIT
if systemctl --user daemon-reload 2>/dev/null; then
  systemctl --user enable quil-badges.service >/dev/null 2>&1 || true
  systemctl --user restart quil-badges.service || echo "warning: could not start quil-badges.service" >&2
fi

if [[ -n "$APPLY" ]]; then
  id="$(awk -v k="$APPLY" '$1 == k { print $2 }' build/lnf_ids.txt)"
  if [[ -z "$id" ]]; then
    echo "unknown variant '$APPLY' (expected one of: $(cut -d' ' -f1 build/lnf_ids.txt | tr '\n' ' '))" >&2
    exit 1
  fi
  args=(--apply "$id")
  (( RESET_LAYOUT )) && args+=(--resetLayout)
  plasma-apply-lookandfeel "${args[@]}"
  # pick up the new window frame without logging out
  qdbus6 org.kde.KWin /KWin reconfigure >/dev/null 2>&1 || true
fi

# Login screen (Plasma Login Manager). It runs as its own user, so this
# copies Quil where that user can read it, which takes root.
if (( LOGIN )); then
  python3 tools/login_screen.py "${APPLY:-dark}"
fi
