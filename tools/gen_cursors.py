#!/usr/bin/env python3
"""Build Quil's cursor themes by recoloring the installed Breeze cursors.

Run by tools/build.py, which puts the result inside the Quil icon themes
(icons/Quil-Dark/cursors and cursors_scalable), so "Quil Dark" is also a
cursor theme. To look at the result on its own:

    python3 tools/gen_cursors.py dark /tmp/quil-cursors

Breeze ships every cursor as an SVG (cursors_scalable/). Each is a white
outline around a black body, plus colored badges and a blurred shadow. This
swaps those colors for Quil's:

    black body      -> "cursor" in palette.json
    white outline   -> "cursor_outline"
    badges          -> positive / negative / neutral / term_blue, with the
                       glyph on them in "accent_fg"
    busy spinner    -> "cursor" and "accent_dim" arcs

KWin and Qt or GTK 4 apps draw the SVGs at any size. Everything else (XWayland,
GTK 3) reads the classic Xcursor files in cursors/, rendered here in SIZES.
"""

import json
import os
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_THEME = "breeze_cursors"
SIZES = [24, 36, 48, 72]          # Xcursor sizes to render (nominal cursor size, px)

SVG = "http://www.w3.org/2000/svg"
SHAPES = {f"{{{SVG}}}{tag}" for tag in ("path", "circle", "rect", "ellipse", "polygon")}
GROUP = f"{{{SVG}}}g"
BLACK = {None, "#000", "#000000", "black", "#0d0d0d", "#0c0c0c", "#0a0a0a", "#070707"}
WHITE = {"#fff", "#ffffff", "white"}
# Breeze color -> palette color
BADGES = {"#11d116": "positive", "#18c087": "positive", "#ed1515": "negative",
          "#3daee9": "term_blue", "#f67400": "neutral"}
SPINNER = {"#46a7ac": "cursor", "#d4497f": "accent_dim"}

ET.register_namespace("", SVG)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")


def source_dir():
    """The installed Breeze cursor theme with SVG cursors, or None."""
    dirs = [os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")]
    dirs += (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    dirs.append("/usr/share")
    for d in dirs:
        theme = Path(d) / "icons" / SOURCE_THEME
        if d and (theme / "cursors_scalable" / "default" / "metadata.json").is_file():
            return theme
    return None


def recolor(svg_text, colors):
    root = ET.fromstring(svg_text)

    def walk(parent, inherited):
        on_badge = False
        for el in parent:
            if el.get("filter") or el.get("id") == "hotspot":
                continue                      # the blurred shadow and the hidden hotspot marker
            fill = el.get("fill", inherited)
            if el.tag == GROUP:
                walk(el, fill)
            elif el.tag in SHAPES:
                if fill in BLACK:
                    el.set("fill", colors["cursor"])
                elif fill in WHITE:
                    # white on top of a badge is its glyph, any other white is outline
                    el.set("fill", colors["accent_fg" if on_badge else "cursor_outline"])
                elif fill in BADGES:
                    el.set("fill", colors[BADGES[fill]])
                    on_badge = True
                elif fill in SPINNER:
                    el.set("fill", colors[SPINNER[fill]])

    walk(root, None)
    return ET.tostring(root, encoding="unicode")


def render(svg, width, height):
    """Render an SVG file to premultiplied BGRA bytes, the pixel format Xcursor uses."""
    rsvg = subprocess.Popen(["rsvg-convert", "-w", str(width), "-h", str(height), str(svg)],
                            stdout=subprocess.PIPE)
    data = subprocess.run(["magick", "png:-", "-alpha", "associate", "-depth", "8", "bgra:-"],
                          stdin=rsvg.stdout, capture_output=True, check=True).stdout
    if rsvg.wait() != 0 or len(data) != width * height * 4:
        raise RuntimeError(f"could not render {svg}")
    return data


def xcursor(images):
    """Pack (nominal size, width, height, xhot, yhot, delay ms, pixels) images into an Xcursor file."""
    header = struct.pack("<4sIII", b"Xcur", 16, 0x10000, len(images))
    toc, chunks, pos = b"", b"", 16 + 12 * len(images)
    for size, w, h, xhot, yhot, delay, pixels in images:
        chunk = struct.pack("<9I", 36, 0xFFFD0002, size, 1, w, h, xhot, yhot, delay) + pixels
        toc += struct.pack("<III", 0xFFFD0002, size, pos)
        chunks += chunk
        pos += len(chunk)
    return header + toc + chunks


def build_cursor(src, scalable, xcursors, colors):
    name = src.name
    frames = json.loads((src / "metadata.json").read_text())
    out = scalable / name
    out.mkdir(parents=True)
    (out / "metadata.json").write_text(json.dumps(frames, indent=4) + "\n")
    images = []
    for frame in frames:
        svg = out / frame["filename"]
        svg.write_text(recolor((src / frame["filename"]).read_text(), colors))
        root = ET.parse(svg).getroot()
        for size in SIZES:
            scale = size / frame["nominal_size"]
            w, h = round(float(root.get("width")) * scale), round(float(root.get("height")) * scale)
            images.append((size, w, h, round(frame["hotspot_x"] * scale), round(frame["hotspot_y"] * scale),
                           frame.get("delay", 0), render(svg, w, h)))
    images.sort(key=lambda image: image[0])   # stable: frames stay in order within a size
    (xcursors / name).write_bytes(xcursor(images))


def generate(colors, dest):
    """Write cursors/ and cursors_scalable/ into dest. Returns False without Breeze's SVG cursors."""
    source = source_dir()
    if source is None:
        return False
    scalable, xcursors = dest / "cursors_scalable", dest / "cursors"
    xcursors.mkdir(parents=True)
    entries = sorted((source / "cursors_scalable").iterdir())
    real = [e for e in entries if e.is_dir() and not e.is_symlink()]
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        list(pool.map(lambda src: build_cursor(src, scalable, xcursors, colors), real))
    # Breeze's alternative names (hand2 -> pointer, ...), for both kinds of cursor
    # (an alias may point at another alias, so check where it ends up)
    for link in (e for e in entries if e.is_symlink()):
        if (scalable / link.resolve().name).is_dir():
            (scalable / link.name).symlink_to(os.readlink(link))
            (xcursors / link.name).symlink_to(os.readlink(link))
    return True


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    variants = json.loads((ROOT / "palette.json").read_text())["variants"]
    if not generate(variants[sys.argv[1]]["colors"], Path(sys.argv[2])):
        sys.exit(f"gen_cursors: the {SOURCE_THEME} cursor theme with SVG cursors is not installed")


if __name__ == "__main__":
    main()
