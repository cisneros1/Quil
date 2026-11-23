#!/usr/bin/env python3
"""Generate Quil's window frame (Aurorae): square frame, 2px border, soft shadow.

Writes the {{token}} template src/aurorae/decoration.svg and the Padding*
lines of the theme's rc file; tools/build.py then fills in the palette colors.
Re-run this after changing the numbers below:

    python3 tools/gen_aurorae.py && ./install.sh

How the frame is built (FrameSvg, 9 elements per state):
- Aurorae stretches the frame over the window plus its "padding" on every
  side, and KWin shows whatever is drawn in the padding as the window shadow.
- Each border element is therefore the shadow (outside) followed by a thin
  slice of the window (inside): the border line and the title bar fill.
- The slice is the same fraction of every element (INNER_RATIO), so a corner
  can be one elliptical gradient that lines up with the edges beside it.
- The shadow reaches further below the window than above it, which reads as
  light coming from above.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "aurorae"

# ------------------------------------------------------------------ tunables
SHADOW = {"top": 16, "left": 24, "right": 24, "bottom": 32}   # how far the shadow reaches
INNER_RATIO = 0.25         # window slice of each border element, relative to its shadow
BORDER = 2                 # border line thickness
HEADER_ALPHA = 0.75        # title bar and frame opacity (KWin blurs what's behind)
INACTIVE_SHADOW = 0.6      # unfocused windows cast a lighter shadow
# shadow falloff: (distance from the window as a fraction of the reach, fraction of full strength)
SHADOW_STOPS = [(0, 1), (0.2, 0.62), (0.45, 0.28), (0.7, 0.09), (1, 0)]
EDGE = 16                  # length of the stretched edge elements
PLAIN = 8                  # element size of the maximized frames (no border, no shadow)

INNER = {side: reach * INNER_RATIO for side, reach in SHADOW.items()}
CORNERS = {"topleft": ("left", "top"), "topright": ("right", "top"),
           "bottomleft": ("left", "bottom"), "bottomright": ("right", "bottom")}
GRID = {"topleft": (0, 0), "top": (1, 0), "topright": (2, 0),
        "left": (0, 1), "center": (1, 1), "right": (2, 1),
        "bottomleft": (0, 2), "bottom": (1, 2), "bottomright": (2, 2)}


def f(n):
    return f"{round(n, 4):g}"


def rect(x, y, w, h, fill, opacity=1):
    op = "" if opacity == 1 else f' fill-opacity="{opacity}"'
    return f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{fill}"{op}/>'


def bounds(x, y, w, h):
    """Invisible rect that pins an element's bounding box to its cell."""
    return rect(x, y, w, h, "#000", 0)


def group(id_, parts):
    return f'  <g id="{id_}">{"".join(parts)}</g>'


def cells(ox, oy, left, top, right, bottom):
    """Yield (name, x, y, w, h) for a 3x3 frame with the given border sizes."""
    cols = [(ox, left), (ox + left + 2, EDGE), (ox + left + EDGE + 4, right)]
    rows = [(oy, top), (oy + top + 2, EDGE), (oy + top + EDGE + 4, bottom)]
    for name, (gx, gy) in GRID.items():
        (x, w), (y, h) = cols[gx], rows[gy]
        yield name, x, y, w, h


def stops(strength, start=0):
    """Gradient stops; `start` is where the falloff begins (the window slice comes first)."""
    return "".join(
        f'<stop offset="{f(start + (1 - start) * d)}" stop-color="{{{{shadow}}}}" '
        f'stop-opacity="{f(strength * a)}"/>' for d, a in SHADOW_STOPS)


def shadowed_frame(prefix, ox, oy, border, header, strength):
    """A frame with border line, translucent fill and shadow. Returns (defs, groups, width)."""
    size = {side: SHADOW[side] + INNER[side] for side in SHADOW}
    plateau = INNER_RATIO / (1 + INNER_RATIO)   # the window slice, as a fraction of an element
    shade = 'fill-opacity="{{shadow_opacity}}"'
    defs, out = [], []
    for name, x, y, w, h in cells(ox, oy, size["left"], size["top"], size["right"], size["bottom"]):
        gid = f"{prefix}-shadow-{name}"
        parts = [bounds(x, y, w, h)]
        if name == "center":
            parts.append(rect(x, y, w, h, header, HEADER_ALPHA))
        elif name in CORNERS:
            sx, sy = CORNERS[name]
            iw, ih = INNER[sx], INNER[sy]
            wx = x + (w - iw if sx == "left" else 0)        # the window slice of this corner
            wy = y + (h - ih if sy == "top" else 0)
            # gradient centered on the cell's inner corner, in bounding-box units
            cx, cy = (1 if sx == "left" else 0), (1 if sy == "top" else 0)
            defs.append(f'    <radialGradient id="{gid}" cx="{cx}" cy="{cy}" fx="{cx}" fy="{cy}" r="1">'
                        f"{stops(strength, plateau)}</radialGradient>")
            # the cell minus the window slice
            d = (f"M{f(x)},{f(y)} H{f(x + w)} V{f(y + h)} H{f(x)} Z "
                 f"M{f(wx)},{f(wy)} H{f(wx + iw)} V{f(wy + ih)} H{f(wx)} Z")
            parts.append(f'<path d="{d}" fill="url(#{gid})" {shade} fill-rule="evenodd"/>')
            # border line along the two outer sides, fill inside it
            bx = wx if sx == "left" else wx + iw - BORDER
            by = wy if sy == "top" else wy + ih - BORDER
            parts.append(rect(wx, by, iw, BORDER, border))
            parts.append(rect(bx, wy + (BORDER if sy == "top" else 0), BORDER, ih - BORDER, border))
            parts.append(rect(wx + (BORDER if sx == "left" else 0), wy + (BORDER if sy == "top" else 0),
                              iw - BORDER, ih - BORDER, header, HEADER_ALPHA))
        else:
            reach, inner = SHADOW[name], INNER[name]
            x1, y1, x2, y2 = {"top": (0, 1, 0, 0), "bottom": (0, 0, 0, 1),
                              "left": (1, 0, 0, 0), "right": (0, 0, 1, 0)}[name]
            defs.append(f'    <linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
                        f"{stops(strength)}</linearGradient>")
            sh, line, fill = {
                "top": ((x, y, w, reach), (x, y + reach, w, BORDER),
                        (x, y + reach + BORDER, w, inner - BORDER)),
                "bottom": ((x, y + inner, w, reach), (x, y + inner - BORDER, w, BORDER),
                           (x, y, w, inner - BORDER)),
                "left": ((x, y, reach, h), (x + reach, y, BORDER, h),
                         (x + reach + BORDER, y, inner - BORDER, h)),
                "right": ((x + inner, y, reach, h), (x + inner - BORDER, y, BORDER, h),
                          (x, y, inner - BORDER, h)),
            }[name]
            parts.append(rect(*sh, f"url(#{gid})").replace("/>", f" {shade}/>"))
            parts.append(rect(*line, border))
            parts.append(rect(*fill, header, HEADER_ALPHA))
        out.append(group(f"{prefix}-{name}", parts))
    return defs, out, size["left"] + EDGE + size["right"] + 4


def plain_frame(prefix, ox, oy, header):
    """Maximized windows: title bar fill only."""
    out = [group(f"{prefix}-{name}", [rect(x, y, w, h, header, HEADER_ALPHA)])
           for name, x, y, w, h in cells(ox, oy, PLAIN, PLAIN, PLAIN, PLAIN)]
    return out, 2 * PLAIN + EDGE + 4


def decoration_svg():
    defs, body, x = [], [], 0
    for prefix, border, header, strength in (
            ("decoration", "{{border_active}}", "{{header}}", 1),
            ("decoration-inactive", "{{border}}", "{{header_inactive}}", INACTIVE_SHADOW)):
        d, groups, width = shadowed_frame(prefix, x, 0, border, header, strength)
        defs += d
        body += [f"  <!-- {prefix} -->"] + groups
        x += width + 10
    for prefix, header in (("decoration-maximized", "{{header}}"),
                           ("decoration-maximized-inactive", "{{header_inactive}}")):
        groups, width = plain_frame(prefix, x, 0, header)
        body += [f"  <!-- {prefix} -->"] + groups
        x += width + 10
    height = SHADOW["top"] + INNER["top"] + EDGE + SHADOW["bottom"] + INNER["bottom"] + 4
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            "<!-- {{full_name}} window frame (Aurorae). Generated by tools/gen_aurorae.py. -->\n"
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{f(x - 10)}" height="{f(height)}" '
            f'viewBox="0 0 {f(x - 10)} {f(height)}">\n'
            "  <defs>\n" + "\n".join(defs) + "\n  </defs>\n" + "\n".join(body) + "\n</svg>\n")


def main():
    for side, inner in INNER.items():
        if inner != int(inner) or inner <= BORDER:
            raise SystemExit(f"gen_aurorae: SHADOW[{side!r}] * INNER_RATIO must be a whole number above {BORDER}")
    svg = OUT / "decoration.svg"
    svg.write_text(decoration_svg())
    print(f"wrote {svg.relative_to(ROOT)}")

    # The rc file tells Aurorae how much of the frame is shadow.
    rc = OUT / "{{slug}}rc"
    text = rc.read_text()
    for side, reach in SHADOW.items():
        text, n = re.subn(rf"^Padding{side.capitalize()}=.*$", f"Padding{side.capitalize()}={reach}",
                          text, flags=re.M)
        if n != 1:
            raise SystemExit(f"gen_aurorae: no Padding{side.capitalize()} line in {rc.name}")
    rc.write_text(text)
    print(f"wrote {rc.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
