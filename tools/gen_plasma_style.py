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
PANEL_RADIUS = 18          # corner radius of the panel / floating dock
PANEL_MARGIN = 6           # frame margin (Plasma's minimum widget inset)
DOCK_PADDING = 4           # extra panel padding (Plasma adds its small spacing, ~4px)
GLASS_ALPHA = 0.50         # panel body opacity when KWin blur is available
SOLID_ALPHA = 0.94         # panel body opacity without blur
RIM_ALPHA = 0.30           # turquoise outline opacity
SHEEN_ALPHA = 0.10         # white highlight along the top inner edge

TASK_WIDTH = 78            # measured Task Manager button width in the dock (logical px)
TASK_CELL = 16             # task button corner cell (cross direction)
TASK_RADIUS = 10           # hover tile corner radius
TASK_MARGIN = 3            # padding between the button edge and the icon
ICON_GAP = 9               # padding on the indicator side: the bar sits just below the icon
BAR = 3                    # indicator thickness
BAR_GAP = 9                # indicator distance from the panel-side edge (tucks under the icon art)
BAR_SHORT = 10             # indicator length for open / minimized apps
BAR_LONG = 18              # indicator length for the active app

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


def cells(ox, oy, cw, ch, e=16):
    """Yield (name, x, y, w, h) for a 3x3 frame whose corners are cw x ch and middle cells e."""
    cols = [(ox, cw), (ox + cw + 2, e), (ox + cw + e + 4, cw)]
    rows = [(oy, ch), (oy + ch + 2, e), (oy + ch + e + 4, ch)]
    for name, (gx, gy) in GRID.items():
        (x, w), (y, h) = cols[gx], rows[gy]
        yield name, x, y, w, h


def frame_size(cw, ch, e=16):
    return 2 * cw + e + 4, 2 * ch + e + 4


def rounded_cell(name, x, y, w, h, r):
    """Fill shapes for one cell of a rounded rectangle whose corners have radius r."""
    if name not in CORNERS:
        return [("rect", (x, y, w, h))]
    sx, sy = CORNERS[name]
    cx = x + (r if sx < 0 else w - r)
    cy = y + (r if sy < 0 else h - r)
    shapes = [("path", wedge(cx, cy, sx, sy, r))]
    rx0, rx1 = (cx, x + w) if sx < 0 else (x, cx)   # columns beside the rounded square
    ry0, ry1 = (cy, y + h) if sy < 0 else (y, cy)   # rows beside the rounded square
    if rx1 > rx0:
        shapes.append(("rect", (rx0, y, rx1 - rx0, h)))
    if ry1 > ry0:
        shapes.append(("rect", (x if sx < 0 else cx, ry0, r, ry1 - ry0)))
    return shapes


def mask_frame(prefix, ox, oy, cw, ch, r):
    out = []
    for name, x, y, w, h in cells(ox, oy, cw, ch):
        parts = [bounds(x, y, w, h)]
        for kind, shape in rounded_cell(name, x, y, w, h, r):
            parts.append(path(shape, "#000") if kind == "path" else rect(*shape, "#000"))
        out.append(group(f"mask-{prefix}{name}", parts))
    return out


def outline(name, x, y, w, h, r, color, opacity, inset=0.5):
    """1px outline segment of a rounded rectangle, drawn inside the cell."""
    if name == "center":
        return []
    if name in CORNERS:
        sx, sy = CORNERS[name]
        cx = x + (r if sx < 0 else w - r)
        cy = y + (r if sy < 0 else h - r)
        d = arc(cx, cy, sx, sy, r - inset)
        hx0, hx1 = (cx, x + w) if sx < 0 else (x, cx)
        vy0, vy1 = (cy, y + h) if sy < 0 else (y, cy)
        hy, vx = cy + sy * (r - inset), cx + sx * (r - inset)
        if hx1 > hx0:
            d += f" M{f(hx0)},{f(hy)} H{f(hx1)}"
        if vy1 > vy0:
            d += f" M{f(vx)},{f(vy0)} V{f(vy1)}"
        return [stroke(d, color, opacity)]
    edge = {"top": (x, y + inset - 0.5, w, 1), "bottom": (x, y + h - inset - 0.5, w, 1),
            "left": (x + inset - 0.5, y, 1, h), "right": (x + w - inset - 0.5, y, 1, h)}[name]
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
    for name, x, y, w, h in cells(0, 0, K, K, K):
        parts = [bounds(x, y, w, h)]
        if name == "center":
            parts += [rect(x, y, w, h, "{{bg}}", alpha), rect(x, y, w, h, "url(#tint)")]
        else:
            parts += outline(name, x, y, w, h, K, "{{accent}}", RIM_ALPHA)
            if name in ("top", "topleft", "topright"):
                parts += outline(name, x, y, w, h, K, "#ffffff", SHEEN_ALPHA, inset=1.5)
        body.append(group(name, parts))
    for name, x, y, w, h in cells(block + 10, 0, K, K, K):
        parts = [bounds(x, y, w, h)]
        for kind, shape in rounded_cell(name, x, y, w, h, K):
            parts.append(path(shape, "#000") if kind == "path" else rect(*shape, "#000"))
        body.append(group(f"mask-{name}", parts))
    hx = 2 * (block + 10)
    for i, side in enumerate(EDGES):
        body.append(group(f"hint-{side}-margin", [bounds(hx + i * 10, 0, PANEL_MARGIN, PANEL_MARGIN)]))
        # Plasma pads panel contents by the "thick-" margins plus its small spacing
        body.append(group(f"thick-hint-{side}-margin", [bounds(hx + i * 10, 30, DOCK_PADDING, DOCK_PADDING)]))
    body.append(group("thick-center", [bounds(hx, 40, 4, 4)]))
    body.append(group("hint-compose-over-border", [bounds(hx, 20, 4, 4)]))
    return svg_doc(hx + 40, block, body, "panel background")


# ------------------------------------------------------------- task manager
# Each Task Manager button is a frame. The indicator bar lives in the edge cell
# that faces the screen edge; its corner cells are wide, so the visible bar is
# TASK_WIDTH - 2 * corner + BAR long (the corners hold its rounded caps).
#
# frame -> (tile, bar color, bar length). Plasma looks up "<state>-hover" first
# when the pointer is over a button, then "hover", then the plain state.
FRAMES = {
    "normal":              (False, "{{accent_dim}}", BAR_SHORT),
    "focus":               (False, "{{accent}}", BAR_LONG),
    "minimized":           (False, "{{fg_muted}}", BAR_SHORT),
    "attention":           (False, "{{neutral}}", BAR_LONG),
    # Hovering shows no background; these keep the bar visible (and the icon's
    # margins stable) while the pointer is over a button.
    "normal-hover":        (False, "{{accent_dim}}", BAR_SHORT),
    "focus-hover":         (False, "{{accent}}", BAR_LONG),
    "minimized-hover":     (False, "{{fg_muted}}", BAR_SHORT),
    "attention-hover":     (False, "{{neutral}}", BAR_LONG),
    "hover":               (False, None, 0),
    "launcher-hover":      (False, None, 0),
    "progress":            ("progress", None, 0),
}
TILE = ("#ffffff", 0.10, "#ffffff", 0.12)          # fill, fill opacity, outline, outline opacity
PROGRESS = ("{{accent}}", 0.18, None, 0)
# panel location prefix -> the button edge that faces the screen edge
ORIENTATIONS = {"": "bottom", "north-": "top", "west-": "left", "east-": "right"}


def bar(name, x, y, w, h, side, color):
    """Indicator bar along `side`; the corner cells next to it hold its rounded caps."""
    if side not in name:
        return []
    r = BAR / 2
    if side in ("top", "bottom"):
        cy = y + BAR_GAP + r if side == "top" else y + h - BAR_GAP - r
        if name == side:
            return [rect(x, cy - r, w, BAR, color)]
        sx = CORNERS[name][0]
        ex = x + w if sx < 0 else x
        sweep = 0 if sx < 0 else 1
        return [path(f"M{f(ex)},{f(cy - r)} A{f(r)},{f(r)} 0 0 {sweep} {f(ex)},{f(cy + r)} Z", color)]
    cx = x + BAR_GAP + r if side == "left" else x + w - BAR_GAP - r
    if name == side:
        return [rect(cx - r, y, BAR, h, color)]
    sy = CORNERS[name][1]
    ey = y + h if sy < 0 else y
    sweep = 1 if sy < 0 else 0
    return [path(f"M{f(cx - r)},{f(ey)} A{f(r)},{f(r)} 0 0 {sweep} {f(cx + r)},{f(ey)} Z", color)]


def task_frame(prefix, ox, oy, state, side):
    tile, bar_color, bar_len = FRAMES[state]
    fill, fill_op, rim, rim_op = PROGRESS if tile == "progress" else TILE if tile else (None, 0, None, 0)
    # corner size along the bar, so the bar between the caps is bar_len long
    along = (TASK_WIDTH + BAR - bar_len) / 2 if bar_color else TASK_CELL
    cw, ch = (along, TASK_CELL) if side in ("top", "bottom") else (TASK_CELL, along)
    p = f"{prefix}{state}-"
    out = []
    for name, x, y, w, h in cells(ox, oy, cw, ch):
        parts = [bounds(x, y, w, h)]
        if name == "center" and fill:
            parts.append(rect(x, y, w, h, fill, fill_op))
        if rim:
            parts += outline(name, x, y, w, h, TASK_RADIUS, rim, rim_op)
        if bar_color:
            parts += bar(name, x, y, w, h, side, bar_color)
        out.append(group(p + name, parts))
    fw, fh = frame_size(cw, ch)
    hx = ox + fw + 4
    for i, m in enumerate(EDGES):
        size = ICON_GAP if m == side else TASK_MARGIN
        out.append(group(f"{p}hint-{m}-margin", [bounds(hx, oy + i * 12, size, size)]))
    if fill:
        out.append(group(f"{p}hint-compose-over-border", [bounds(hx, oy + 50, 4, 4)]))
        out += mask_frame(p, ox, oy + fh + 4, cw, ch, TASK_RADIUS)
    return out


def tasks_svg():
    along = (TASK_WIDTH + BAR - min(BAR_SHORT, BAR_LONG)) / 2
    fw, fh = frame_size(along, along)
    bw, bh = fw + 24, 2 * fh + 8
    body = []
    for row, (prefix, side) in enumerate(ORIENTATIONS.items()):
        for col, state in enumerate(FRAMES):
            body += task_frame(prefix, col * bw, row * bh, state, side)
    # Some Plasma versions look the compose hint up without the state prefix.
    body.append(group("hint-compose-over-border", [bounds(0, len(ORIENTATIONS) * bh, 4, 4)]))
    return svg_doc(f(len(FRAMES) * bw), f(len(ORIENTATIONS) * bh + 4), body, "task manager")


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
