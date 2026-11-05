#!/usr/bin/env python3
"""Render every Quil variant from src/ templates into build/share/.

build/share/ mirrors ~/.local/share, so installing is a plain copy.

Templates use {{token}} placeholders:
  {{accent}}      -> "#d6a65c"      (any color in palette.json, as hex)
  {{accent.rgb}}  -> "214,166,92"   (KDE .colors / rc format)
  {{full_name}}   -> "Quil Dark"    (metadata; see context() below)
Tokens work in file *names* too, e.g. src/color-schemes/{{scheme}}.colors.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

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
}

TOKEN = re.compile(r"\{\{\s*([A-Za-z_]\w*)(?:\.(rgb))?\s*\}\}")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def die(msg):
    sys.exit(f"build: error: {msg}")


def context(meta, key, variant):
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
    }


def render(text, ctx, colors, where):
    def sub(m):
        name, fmt = m.group(1), m.group(2)
        if name in colors:
            h = colors[name].lstrip("#")
            return ",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4)) if fmt else colors[name]
        if name in ctx and not fmt:
            return str(ctx[name])
        die(f"{where}: unknown token {m.group(0)}")
    return TOKEN.sub(sub, text)


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
        ctx, colors = context(meta, key, variant), variant["colors"]
        print(f"building {ctx['full_name']}")

        for component, target in COMPONENTS.items():
            dest_rel = render(target, ctx, colors, target)
            render_tree(SRC / component, SHARE / dest_rel, ctx, colors)
            if component == "color-schemes":
                manifest.update(str(p.relative_to(SHARE)) for p in (SHARE / dest_rel).iterdir())
            else:
                manifest.add(dest_rel)
        lnf_ids.append(f"{key} {ctx['lnf_id']}")

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
