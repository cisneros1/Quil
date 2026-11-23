#!/usr/bin/env python3
"""Render every Quil variant from src/ templates into build/share/.

build/share/ mirrors ~/.local/share, so installing is a plain copy.

Templates use {{token}} placeholders:
  {{accent}}      -> "#d6a65c"      (any color in palette.json, as hex)
  {{accent.rgb}}  -> "214,166,92"   (KDE .colors / rc format)
  {{accent 30% on view}} -> "#2e4c45"  (two palette colors mixed)
  {{full_name}}   -> "Quil Dark"    (metadata; see context() below)
  {{font}}        -> "Inter,10,-1,5,400,..."   (fonts block of palette.json)
Tokens work in file *names* too, e.g. src/color-schemes/{{scheme}}.colors.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import gen_cursors

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
BUILD = ROOT / "build"
SHARE = BUILD / "share"

# src/<component>/ -> where it is installed, relative to ~/.local/share
COMPONENTS = {
    "color-schemes": "color-schemes",
    "desktoptheme": "plasma/desktoptheme/{{slug}}",
    "aurorae": "aurorae/themes/{{slug}}",
    "look-and-feel": "plasma/look-and-feel/{{lnf_id}}",
    "icons": "icons/{{slug}}",
    "plasmoid": "plasma/plasmoids/{{id_prefix}}.dock",   # same for every variant
    "helper": "quil",                                       # badge relay for Quil Dock
    "dbus-services": "dbus-1/services",
    "konsole": "konsole",                                   # terminal colors + profile
    "syntax": "org.kde.syntax-highlighting/themes",         # Kate, KWrite, KDevelop
}
# Components installed into directories shared with other packages: track their files, not the dir.
SHARED_DIRS = {"color-schemes", "dbus-services", "konsole", "syntax"}

TOKEN = re.compile(r"\{\{\s*([A-Za-z_]\w*)(?:\.(rgb))?\s*\}\}")
MIX = re.compile(r"\{\{\s*([A-Za-z_]\w*)\s+(\d+)%\s+on\s+([A-Za-z_]\w*)\s*\}\}")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def die(msg):
    sys.exit(f"build: error: {msg}")


def have_qt_plugin(rel):
    dirs = [d for d in os.environ.get("QT_PLUGIN_PATH", "").split(":") if d]
    if shutil.which("qtpaths6"):
        dirs.append(subprocess.run(["qtpaths6", "--query", "QT_INSTALL_PLUGINS"],
                                   capture_output=True, text=True).stdout.strip())
    dirs.append("/usr/lib/qt6/plugins")
    return any((Path(d) / rel).exists() for d in dirs if d)


def widget_style():
    """Darkly (rounded, translucent menus) when it's installed, else Breeze."""
    return "Darkly" if have_qt_plugin("styles/darkly6.so") else "Breeze"


def decoration_plugin():
    """Aurorae's newer engine for SVG themes where it exists (KWin moves SVG themes
    to it at login anyway), else the original one."""
    v2 = "org.kde.kwin.aurorae.v2"
    return v2 if have_qt_plugin(f"org.kde.kdecoration3/{v2}.so") else "org.kde.kwin.aurorae"


def qfont(family, size, weight=400):
    """A font in the QFont::toString() form kdeglobals uses."""
    return f"{family},{size},-1,5,{weight},0,0,0,0,0,0,0,0,0,0,1"


def context(meta, fonts, style, cursors, key, variant):
    name, label = meta["name"], variant["label"]
    return {
        **meta,
        "variant": key,
        "label": label,
        "full_name": f"{name} {label}",
        "slug": f"{name}-{label}",
        "scheme": f"{name}{label}",
        "lnf_id": f"{meta['id_prefix']}.{key}",
        "icons": variant["icons"],
        "description": variant["description"],
        "font": qfont(fonts["ui"], fonts["size"]),
        "font_small": qfont(fonts["ui"], fonts["small_size"]),
        "font_title": qfont(fonts["ui"], fonts["size"], fonts["title_weight"]),
        "font_fixed": qfont(fonts["mono"], fonts["size"]),
        "widget_style": style,
        "decoration_plugin": decoration_plugin(),
        # Quil's cursors live inside its icon themes; without them, Breeze's
        "cursor_theme": f"{name}-{label}" if cursors else gen_cursors.SOURCE_THEME,
        "shadow_opacity": variant["shadow_opacity"],   # window shadow strength, 0 to 1
    }


def render(text, ctx, colors, where):
    def mix(m):
        top, percent, base = m.group(1), int(m.group(2)), m.group(3)
        if top not in colors or base not in colors or percent > 100:
            die(f"{where}: unknown token {m.group(0)}")
        a, b = (colors[c].lstrip("#") for c in (top, base))
        return "#" + "".join(
            f"{round((int(a[i:i + 2], 16) * percent + int(b[i:i + 2], 16) * (100 - percent)) / 100):02x}"
            for i in (0, 2, 4))

    def sub(m):
        name, fmt = m.group(1), m.group(2)
        if name in colors:
            h = colors[name].lstrip("#")
            return ",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4)) if fmt else colors[name]
        if name in ctx and not fmt:
            return str(ctx[name])
        die(f"{where}: unknown token {m.group(0)}")
    return TOKEN.sub(sub, MIX.sub(mix, text))


def load_palette():
    palette = json.loads((ROOT / "palette.json").read_text())
    variants = palette["variants"]
    keys = None
    for key, v in variants.items():
        for cname, value in v["colors"].items():
            if not HEX.match(value):
                die(f"palette.json: {key}.{cname} = {value!r} is not #rrggbb")
        if keys is None:
            keys = set(v["colors"])
        elif set(v["colors"]) != keys:
            die(f"palette.json: variant {key!r} colors differ from the others: "
                f"{sorted(keys ^ set(v['colors']))}")
    return palette


def render_tree(src_dir, dest_dir, ctx, colors):
    for path in sorted(src_dir.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(src_dir)
        out = dest_dir / render(str(rel), ctx, colors, str(rel))
        out.parent.mkdir(parents=True, exist_ok=True)
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            out.write_bytes(data)  # binary asset: copy as-is
            continue
        out.write_text(render(text, ctx, colors, str(path.relative_to(ROOT))))


def need(tool):
    if not shutil.which(tool):
        die(f"'{tool}' is required (rsvg-convert: librsvg, magick: imagemagick)")


def main():
    need("rsvg-convert")
    need("magick")
    palette = load_palette()
    meta = palette["meta"]
    style = widget_style()
    print(f"application style: {style}")
    cursors = gen_cursors.source_dir() is not None
    if not cursors:
        print(f"note: no {gen_cursors.SOURCE_THEME} SVG cursors found, so Quil keeps the Breeze cursors")

    shutil.rmtree(BUILD, ignore_errors=True)
    SHARE.mkdir(parents=True)
    manifest, lnf_ids = set(), []

    wall_rel = f"wallpapers/{meta['name']}"
    wall_dir = SHARE / wall_rel
    manifest.add(wall_rel)
    (wall_dir / "contents").mkdir(parents=True)
    (wall_dir / "metadata.json").write_text(json.dumps({
        "KPlugin": {
            "Authors": [{"Name": meta["author"]}],
            "Id": meta["name"],
            "License": meta["license"],
            "Name": meta["name"],
        }
    }, indent=4) + "\n")

    for key, variant in palette["variants"].items():
        ctx, colors = context(meta, palette["fonts"], style, cursors, key, variant), variant["colors"]
        print(f"building {ctx['full_name']}")

        for component, target in COMPONENTS.items():
            dest_rel = render(target, ctx, colors, target)
            render_tree(SRC / component, SHARE / dest_rel, ctx, colors)
            if component in SHARED_DIRS:
                manifest.update(str(p.relative_to(SHARE)) for p in (SHARE / dest_rel).iterdir())
            else:
                manifest.add(dest_rel)
        lnf_ids.append(f"{key} {ctx['lnf_id']}")

        # Cursors: Breeze's, recolored, inside the icon theme.
        if cursors:
            gen_cursors.generate(colors, SHARE / "icons" / ctx["slug"])

        # Wallpaper: one package, light image in images/, dark in images_dark/.
        svg = BUILD / f"wallpaper-{key}.svg"
        svg.write_text(render((SRC / "wallpaper" / "wallpaper.svg").read_text(), ctx, colors,
                              "src/wallpaper/wallpaper.svg"))
        images = wall_dir / "contents" / ("images_dark" if variant["dark"] else "images")
        images.mkdir()
        png = images / "3840x2160.png"
        subprocess.run(["rsvg-convert", "-w", "3840", "-h", "2160", "-o", png, svg], check=True)

        # Placeholder previews from the wallpaper (replace with real screenshots later).
        previews = SHARE / f"plasma/look-and-feel/{ctx['lnf_id']}/contents/previews"
        previews.mkdir(parents=True, exist_ok=True)
        subprocess.run(["magick", png, "-resize", "640x360", previews / "preview.png"], check=True)
        subprocess.run(["magick", png, "-resize", "1920x1080", "-quality", "90",
                        previews / "fullscreenpreview.jpg"], check=True)

    (BUILD / "manifest.txt").write_text("\n".join(sorted(manifest)) + "\n")
    (BUILD / "lnf_ids.txt").write_text("\n".join(lnf_ids) + "\n")
    print(f"done -> {SHARE.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
