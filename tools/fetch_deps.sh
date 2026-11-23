#!/usr/bin/env bash
# Fetch the third-party icon theme and fonts Quil uses, for the current user,
# when they aren't installed yet. Run by ./install.sh; safe to run again.
#
#   Colloid icon theme   github.com/vinceliuice/Colloid-icon-theme  GPL-3.0
#   Inter                github.com/rsms/inter                      OFL-1.1
#   JetBrains Mono       github.com/JetBrains/JetBrainsMono         OFL-1.1
#
# Which icon themes and fonts are wanted comes from palette.json.
set -euo pipefail
cd "$(dirname "$0")/.."

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
COLLOID_REV=ceac6608ecd0e40025cbc2ebbd32bf0e0f4ebc6a
INTER_URL=https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip
JBMONO_URL=https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

have_icon_theme() {
  local d
  for d in "$HOME/.icons" "$DATA/icons" /usr/local/share/icons /usr/share/icons; do
    [[ -f "$d/$1/index.theme" ]] && return 0
  done
  return 1
}

have_font() { [[ -n "$(fc-list "$1" family)" ]]; }

fetch() {  # url -> file
  echo "downloading $1"
  curl -fL --retry 2 -sS -o "$2" "$1"
}

# --- icon themes ---
mapfile -t ICON_THEMES < <(python3 -c '
import json
for v in json.load(open("palette.json"))["variants"].values(): print(v["icons"])')

colors=()
for theme in "${ICON_THEMES[@]}"; do
  have_icon_theme "$theme" && continue
  if [[ "$theme" =~ ^Colloid-([A-Za-z]+)-(Dark|Light)$ ]]; then
    colors+=("${BASH_REMATCH[1],,}")
  else
    echo "warning: icon theme '$theme' is not installed and Quil doesn't know how to fetch it" >&2
  fi
done
if (( ${#colors[@]} )); then
  fetch "https://github.com/vinceliuice/Colloid-icon-theme/archive/$COLLOID_REV.tar.gz" "$TMP/colloid.tar.gz"
  mkdir "$TMP/colloid"
  tar -xzf "$TMP/colloid.tar.gz" -C "$TMP/colloid" --strip-components=1
  for c in $(printf '%s\n' "${colors[@]}" | sort -u); do
    echo "installing Colloid icon theme ($c) to $DATA/icons"
    # -p: KDE logo instead of Apple's
    (cd "$TMP/colloid" && bash ./install.sh -d "$DATA/icons" -t "$c" -p >/dev/null)
  done
fi

# --- fonts ---
font_of() { python3 -c 'import json, sys; print(json.load(open("palette.json"))["fonts"][sys.argv[1]])' "$1"; }
UI_FONT="$(font_of ui)"
MONO_FONT="$(font_of mono)"

install_fonts() {  # name url glob
  local name="$1" url="$2" glob="$3" dest="$DATA/fonts/$1"
  fetch "$url" "$TMP/$name.zip"
  mkdir -p "$TMP/$name" "$dest"
  python3 -I -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$TMP/$name.zip" "$TMP/$name"
  find "$TMP/$name" -path "$glob" -name '*.ttf' -exec cp {} "$dest/" \;
  echo "installed $name to $dest"
  FONTS_CHANGED=1
}

FONTS_CHANGED=0
for font in "$UI_FONT" "$MONO_FONT"; do
  have_font "$font" && continue
  case "$font" in
    "Inter")          install_fonts Inter "$INTER_URL" '*/extras/ttf/Inter-*' ;;
    "JetBrains Mono") install_fonts JetBrainsMono "$JBMONO_URL" '*/fonts/ttf/JetBrainsMono-*' ;;
    *) echo "warning: font '$font' is not installed and Quil doesn't know how to fetch it" >&2 ;;
  esac
done
(( FONTS_CHANGED )) && fc-cache -f "$DATA/fonts" >/dev/null
exit 0
