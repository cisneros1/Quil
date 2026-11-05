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

while IFS= read -r rel; do
  [[ -z "$rel" ]] && continue
  if [[ -e "$DEST/$rel" ]]; then
    rm -rf "${DEST:?}/$rel"
    echo "removed $DEST/$rel"
  fi
done < build/manifest.txt
