#!/usr/bin/env python3
"""Generate Quil's Plasma style SVG templates (glass panel + task manager).

Writes {{token}} templates into src/desktoptheme/; tools/build.py then fills in
the palette colors. Re-run this after changing the geometry or opacities below:

    python3 tools/gen_plasma_style.py && ./install.sh

How the frames are built (Plasma FrameSvg, 9 elements per frame):
- Translucent fills live only in the "center" element. With the
  "hint-compose-over-border" element present, Plasma stretches the center over
  the whole frame and cuts it to shape with the "mask-*" elements. That avoids
  seams between pieces under fractional display scaling.
- The corner/edge elements carry only the outline, highlight and indicator.
- Every element is drawn with absolute coordinates (no transforms) and has an
  invisible rect pinning its bounds to its cell.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "desktoptheme"

# ------------------------------------------------------------------ tunables
PANEL_RADIUS = 16          # corner radius of the panel / floating dock
PANEL_MARGIN = 6           # padding between the panel edge and its widgets
GLASS_ALPHA = 0.50         # panel body opacity when KWin blur is available
SOLID_ALPHA = 0.94         # panel body opacity without blur
RIM_ALPHA = 0.30           # turquoise outline opacity
SHEEN_ALPHA = 0.10         # white highlight along the top inner edge

TASK_CELL = 16             # task button corner cell (bar length = width - 2 * cell)
TASK_RADIUS = 10           # task button tile corner radius
TASK_MARGIN = 4            # padding between the tile edge and the icon
BAR = 3                    # indicator thickness
BAR_GAP = 2                # indicator distance from the panel-side edge

CORNERS = {"topleft": (-1, -1), "topright": (1, -1), "bottomleft": (-1, 1), "bottomright": (1, 1)}
EDGES = ["top", "bottom", "left", "right"]
GRID = {"topleft": (0, 0), "top": (1, 0), "topright": (2, 0),
        "left": (0, 1), "center": (1, 1), "right": (2, 1),
        "bottomleft": (0, 2), "bottom": (1, 2), "bottomright": (2, 2)}


def f(n):
    return f"{n:g}"


def wedge(cx, cy, sx, sy, r):
    """Quarter disc of radius r with its right angle at (cx, cy), opening toward (sx, sy)."""
    sweep = 1 if sx * sy > 0 else 0
    return f"M{f(cx + sx * r)},{f(cy)} A{f(r)},{f(r)} 0 0 {sweep} {f(cx)},{f(cy + sy * r)} L{f(cx)},{f(cy)} Z"


def arc(cx, cy, sx, sy, r):
    sweep = 1 if sx * sy > 0 else 0
    return f"M{f(cx + sx * r)},{f(cy)} A{f(r)},{f(r)} 0 0 {sweep} {f(cx)},{f(cy + sy * r)}"


def rect(x, y, w, h, fill, opacity=1):
    op = "" if opacity == 1 else f' fill-opacity="{opacity}"'
    return f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{fill}"{op}/>'


def path(d, fill, opacity=1):
    op = "" if opacity == 1 else f' fill-opacity="{opacity}"'
    return f'<path d="{d}" fill="{fill}"{op}/>'


def stroke(d, color, opacity):
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-opacity="{opacity}" stroke-width="1"/>'


def bounds(x, y, w, h):
    """Invisible rect that pins an element's bounding box to its cell."""
    return rect(x, y, w, h, "#000", 0)


def group(id_, parts):
    return f'  <g id="{id_}">{"".join(parts)}</g>'


def cells(ox, oy, k):
    for name, (gx, gy) in GRID.items():
        yield name, ox + gx * (k + 2), oy + gy * (k + 2)


def rounded_cell(name, x, y, k, r):
    """Fill shapes for one cell of a rounded rectangle whose corners have radius r <= k."""
    if name not in CORNERS:
        return [("rect", (x, y, k, k))]
    sx, sy = CORNERS[name]
    cx = x + (r if sx < 0 else k - r)
    cy = y + (r if sy < 0 else k - r)
    shapes = [("path", wedge(cx, cy, sx, sy, r))]
    rx0, rx1 = (cx, x + k) if sx < 0 else (x, cx)   # columns beside the rounded square
    ry0, ry1 = (cy, y + k) if sy < 0 else (y, cy)   # rows beside the rounded square
    if rx1 > rx0:
        shapes.append(("rect", (rx0, y, rx1 - rx0, k)))
    if ry1 > ry0:
        shapes.append(("rect", (x if sx < 0 else cx, ry0, r, ry1 - ry0)))
    return shapes


def mask_frame(prefix, ox, oy, k, r):
    out = []
    for name, x, y in cells(ox, oy, k):
        parts = [bounds(x, y, k, k)]
        for kind, shape in rounded_cell(name, x, y, k, r):
            parts.append(path(shape, "#000") if kind == "path" else rect(*shape, "#000"))
        out.append(group(f"mask-{prefix}{name}", parts))
    return out


def outline(name, x, y, k, r, color, opacity, inset=0.5):
    """1px outline segment of a rounded rectangle, drawn inside the cell."""
    if name == "center":
        return []
    if name in CORNERS:
        sx, sy = CORNERS[name]
        cx = x + (r if sx < 0 else k - r)
        cy = y + (r if sy < 0 else k - r)
        d = arc(cx, cy, sx, sy, r - inset)
        hx0, hx1 = (cx, x + k) if sx < 0 else (x, cx)
        vy0, vy1 = (cy, y + k) if sy < 0 else (y, cy)
        hy, vx = cy + sy * (r - inset), cx + sx * (r - inset)
        if hx1 > hx0:
            d += f" M{f(hx0)},{f(hy)} H{f(hx1)}"
        if vy1 > vy0:
            d += f" M{f(vx)},{f(vy0)} V{f(vy1)}"
        return [stroke(d, color, opacity)]
    edge = {"top": (x, y + inset - 0.5, k, 1), "bottom": (x, y + k - inset - 0.5, k, 1),
            "left": (x + inset - 0.5, y, 1, k), "right": (x + k - inset - 0.5, y, 1, k)}[name]
    return [rect(*edge, color, opacity)]


def svg_doc(w, h, body, comment):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f"<!-- {{{{full_name}}}} {comment}. Generated by tools/gen_plasma_style.py. -->\n"
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
            + "\n".join(body) + "\n</svg>\n")


# ------------------------------------------------------------ panel background
def panel_svg(alpha):
    K = PANEL_RADIUS
    block = 3 * K + 4
    body = [
        "  <defs>",
        # one gradient over the whole panel: white sheen on top, turquoise glow below
        '    <linearGradient id="tint" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#ffffff" stop-opacity="0.07"/>'
        '<stop offset="0.5" stop-color="#ffffff" stop-opacity="0.02"/>'
        '<stop offset="1" stop-color="{{accent}}" stop-opacity="0.09"/></linearGradient>',
        "  </defs>",
    ]
    for name, x, y in cells(0, 0, K):
        parts = [bounds(x, y, K, K)]
        if name == "center":
            parts += [rect(x, y, K, K, "{{bg}}", alpha), rect(x, y, K, K, "url(#tint)")]
        else:
            parts += outline(name, x, y, K, K, "{{accent}}", RIM_ALPHA)
            if name in ("top", "topleft", "topright"):
                parts += outline(name, x, y, K, K, "#ffffff", SHEEN_ALPHA, inset=1.5)
        body.append(group(name, parts))
    body += mask_frame("", block + 10, 0, K, K)
    hx = 2 * (block + 10)
    for i, side in enumerate(EDGES):
        body.append(group(f"hint-{side}-margin", [bounds(hx + i * 10, 0, PANEL_MARGIN, PANEL_MARGIN)]))
    body.append(group("hint-compose-over-border", [bounds(hx, 20, 4, 4)]))
    return svg_doc(hx + 40, block, body, "panel background")


# ------------------------------------------------------------- task manager
# state -> (tile fill, fill opacity, outline color, outline opacity, bar color)
STATES = {
    "normal":    (None, 0, None, 0, "{{accent_dim}}"),
    "focus":     ("#ffffff", 0.09, "{{accent}}", 0.35, "{{accent}}"),
    "hover":     ("#ffffff", 0.11, "#ffffff", 0.14, None),
    "attention": ("{{neutral}}", 0.16, "{{neutral}}", 0.55, "{{neutral}}"),
    "minimized": (None, 0, None, 0, "{{fg_muted}}"),
    "progress":  ("{{accent}}", 0.20, None, 0, None),
}
# panel location prefix -> the button edge that faces the screen edge
ORIENTATIONS = {"": "bottom", "north-": "top", "west-": "left", "east-": "right"}


def bar(name, x, y, k, side, color):
    """Indicator bar along `side`; the corner cells next to it hold its rounded caps."""
    if side not in name:
        return []
    h = BAR / 2
    if side in ("top", "bottom"):
        cy = y + BAR_GAP + h if side == "top" else y + k - BAR_GAP - h
        if name == side:
            return [rect(x, cy - h, k, BAR, color)]
        sx = CORNERS[name][0]
        ex = x + k if sx < 0 else x
        sweep = 0 if sx < 0 else 1
        return [path(f"M{f(ex)},{f(cy - h)} A{f(h)},{f(h)} 0 0 {sweep} {f(ex)},{f(cy + h)} Z", color)]
    cx = x + BAR_GAP + h if side == "left" else x + k - BAR_GAP - h
    if name == side:
        return [rect(cx - h, y, BAR, k, color)]
    sy = CORNERS[name][1]
    ey = y + k if sy < 0 else y
    sweep = 1 if sy < 0 else 0
    return [path(f"M{f(cx - h)},{f(ey)} A{f(h)},{f(h)} 0 0 {sweep} {f(cx + h)},{f(ey)} Z", color)]


def task_frame(prefix, ox, oy, state, side):
    K, R = TASK_CELL, TASK_RADIUS
    fill, fill_op, rim, rim_op, bar_color = STATES[state]
    p = f"{prefix}{state}-"
    out = []
    for name, x, y in cells(ox, oy, K):
        parts = [bounds(x, y, K, K)]
        if name == "center" and fill:
            parts.append(rect(x, y, K, K, fill, fill_op))
        if rim:
            parts += outline(name, x, y, K, R, rim, rim_op)
        if bar_color:
            parts += bar(name, x, y, K, side, bar_color)
        out.append(group(p + name, parts))
    hx = ox + 3 * (K + 2) + 4
    for i, m in enumerate(EDGES):
        out.append(group(f"{p}hint-{m}-margin", [bounds(hx, oy + i * 6, TASK_MARGIN, TASK_MARGIN)]))
    if fill:
        out.append(group(f"{p}hint-compose-over-border", [bounds(hx, oy + 26, 4, 4)]))
        out += mask_frame(p, ox, oy + 3 * (K + 2) + 4, K, R)
    return out


def tasks_svg():
    K = TASK_CELL
    bw, bh = 3 * K + 4 + 12, 2 * (3 * K + 4) + 8
    body = []
    for row, (prefix, side) in enumerate(ORIENTATIONS.items()):
        for col, state in enumerate(STATES):
            body += task_frame(prefix, col * bw, row * bh, state, side)
    # Some Plasma versions look the compose hint up without the state prefix.
    body.append(group("hint-compose-over-border", [bounds(0, len(ORIENTATIONS) * bh, 4, 4)]))
    return svg_doc(len(STATES) * bw, len(ORIENTATIONS) * bh + 4, body, "task manager")


def main():
    files = {
        OUT / "widgets" / "panel-background.svg": panel_svg(SOLID_ALPHA),
        OUT / "translucent" / "widgets" / "panel-background.svg": panel_svg(GLASS_ALPHA),
        OUT / "widgets" / "tasks.svg": tasks_svg(),
    }
    for p, text in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        print(f"wrote {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
