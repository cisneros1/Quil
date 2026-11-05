#!/usr/bin/env python3
"""Give apps rounded-square icons inside Quil's icon themes.

Quil's icon themes (Quil-Dark, Quil-Light) inherit Breeze and contain only
rounded copies of app icons. For each app this script finds its icon in the
base theme, renders it at 512px, clips the visible artwork to a rounded square
and saves it under the same icon name, so the dock and menus pick it up.
Every icon's artwork is scaled to the same size (FILL), so icons with extra
built-in padding don't look smaller. Already-rounded or circular icons keep
their shape.

    tools/round_icons.py                    # every app pinned in a Task Manager
    tools/round_icons.py org.kde.dolphin    # plus specific apps (desktop file ids)

Run by ./install.sh. Needs rsvg-convert and magick.
"""

import configparser
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()
DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share"))
DATA_DIRS = [DATA_HOME] + [Path(p) for p in os.environ.get(
    "XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":") if p]
DATA_DIRS += [DATA_HOME / "flatpak/exports/share", Path("/var/lib/flatpak/exports/share")]
ICON_ROOTS = [HOME / ".icons"] + [d / "icons" for d in DATA_DIRS]
APPLETS_RC = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "plasma-org.kde.plasma.desktop-appletsrc"

SIZE = 512
RADIUS = 0.225      # corner radius as a fraction of the artwork's shorter side
FILL = 0.90         # every icon's artwork is scaled to this fraction of the canvas


def pinned_launchers():
    if not APPLETS_RC.exists():
        return []
    apps = []
    for line in APPLETS_RC.read_text(errors="replace").splitlines():
        if line.startswith("launchers="):
            for entry in line.split("=", 1)[1].split(","):
                entry = entry.strip()
                if entry.startswith("applications:"):
                    apps.append(entry.removeprefix("applications:"))
                elif entry.startswith("file://") and entry.endswith(".desktop"):
                    apps.append(entry.removeprefix("file://"))
    return list(dict.fromkeys(apps))


def desktop_file(app):
    if app.startswith("/"):
        return Path(app) if Path(app).exists() else None
    name = app if app.endswith(".desktop") else app + ".desktop"
    for d in DATA_DIRS:
        p = d / "applications" / name
        if p.exists():
            return p
    return None


def icon_of(desktop):
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str
    cp.read(desktop, encoding="utf-8")
    return cp.get("Desktop Entry", "Icon", fallback=None)


def theme_chain(theme):
    chain, todo = [], [theme]
    while todo:
        t = todo.pop(0)
        if t in chain:
            continue
        chain.append(t)
        for root in ICON_ROOTS:
            index = root / t / "index.theme"
            if index.exists():
                m = re.search(r"^Inherits=(.*)$", index.read_text(errors="replace"), re.M)
                if m:
                    todo += [x.strip() for x in m.group(1).split(",") if x.strip()]
                break
    if "hicolor" not in chain:
        chain.append("hicolor")
    return chain


def find_icon(name, chain):
    def score(p):
        nums = [int(n) for n in re.findall(r"(?<![\d.])(\d{2,3})(?![\d.])", str(p.parent))]
        size = 1024 if "scalable" in p.parts or not nums else max(nums)
        return (size, p.suffix in (".svg", ".svgz"))

    for theme in chain:
        found = []
        for root in ICON_ROOTS:
            base = root / theme
            if base.is_dir():
                found += [p for ext in ("svg", "svgz", "png") for p in base.rglob(f"{name}.{ext}")]
        if found:
            return max(found, key=score)
    for ext in ("svg", "png", "xpm"):
        p = Path("/usr/share/pixmaps") / f"{name}.{ext}"
        if p.exists():
            return p
    return None


def run(*args):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True, text=True).stdout


def artwork_box(png, src):
    box = run("magick", png, "-alpha", "extract", "-threshold", "50%", "-format", "%@", "info:").strip()
    m = re.fullmatch(r"(\d+)x(\d+)\+(\d+)\+(\d+)", box)
    if not m:
        raise RuntimeError(f"no visible artwork in {src}")
    w, h, x, y = map(int, m.groups())
    return x, y, w, h


def round_icon(src, dest, tmp):
    base = tmp / "base.png"
    if src.suffix in (".svg", ".svgz"):
        run("rsvg-convert", "-w", SIZE, "-h", SIZE, "--keep-aspect-ratio", "-o", base, src)
    else:
        run("magick", src, "-background", "none", "-resize", f"{SIZE}x{SIZE}", base)
    run("magick", base, "-background", "none", "-gravity", "center", "-extent", f"{SIZE}x{SIZE}", base)
    # Crop to the solid artwork (ignoring soft drop shadows) and scale it to FILL of
    # the canvas, so icons with different built-in padding all appear the same size.
    x, y, w, h = artwork_box(base, src)
    target = round(FILL * SIZE)
    run("magick", base, "-crop", f"{w}x{h}+{x}+{y}", "+repage", "-resize", f"{target}x{target}",
        "-background", "none", "-gravity", "center", "-extent", f"{SIZE}x{SIZE}", base)
    x, y, w, h = artwork_box(base, src)
    r = round(RADIUS * min(w, h))
    mask = tmp / "mask.png"
    run("magick", "-size", f"{SIZE}x{SIZE}", "xc:none", "-fill", "white",
        "-draw", f"roundrectangle {x},{y} {x + w - 1},{y + h - 1} {r},{r}", mask)
    dest.parent.mkdir(parents=True, exist_ok=True)
    run("magick", base, mask, "-compose", "DstIn", "-composite", dest)


def main():
    for tool in ("rsvg-convert", "magick"):
        if not shutil.which(tool):
            sys.exit(f"round_icons: '{tool}' is required")
    palette = json.loads((ROOT / "palette.json").read_text())
    meta = palette["meta"]
    apps = pinned_launchers() + sys.argv[1:]
    if not apps:
        print("round_icons: no pinned apps found")
        return

    for key, variant in palette["variants"].items():
        slug = f"{meta['name']}-{variant['label']}"
        out_dir = DATA_HOME / "icons" / slug / f"apps/{SIZE}"
        chain = theme_chain(variant["icons"])
        with tempfile.TemporaryDirectory() as tmp:
            for app in apps:
                desktop = desktop_file(app)
                icon = icon_of(desktop) if desktop else None
                if not icon:
                    print(f"  skip {app}: no desktop file or icon")
                    continue
                if icon.startswith("/"):
                    print(f"  skip {app}: icon is a file path ({icon}), not a themeable name")
                    continue
                src = find_icon(icon, chain)
                if not src:
                    print(f"  skip {app}: icon '{icon}' not found")
                    continue
                round_icon(src, out_dir / f"{icon}.png", Path(tmp))
                print(f"  {slug}: {icon} <- {src}")

    # make KDE re-read icons
    cache = HOME / ".cache" / "icon-cache.kcache"
    cache.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
