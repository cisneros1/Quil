#!/usr/bin/env bash
# Build Quil and install it for the current user (~/.local/share).
#   ./install.sh                 build + install both variants
#   ./install.sh --apply dark    ...then switch to Quil Dark (or: light)
#   ./install.sh --apply dark --reset-layout   ...also apply Quil's panel layout
set -euo pipefail
cd "$(dirname "$0")"

DEST="${XDG_DATA_HOME:-$HOME/.local/share}"
APPLY=""
RESET_LAYOUT=0

usage() { sed -n '2,5p' "$0" | sed 's/^# \{0,1\}//'; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY="${2:-}"; shift 2 ;;
    --reset-layout) RESET_LAYOUT=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

python3 tools/build.py

while IFS= read -r rel; do
  [[ -z "$rel" ]] && continue
  rm -rf "${DEST:?}/$rel"
  mkdir -p "$(dirname "$DEST/$rel")"
  cp -r "build/share/$rel" "$DEST/$rel"
  echo "installed $DEST/$rel"
done < build/manifest.txt

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
fi
