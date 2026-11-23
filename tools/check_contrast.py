#!/usr/bin/env python3
"""Check the contrast of every text color in palette.json (WCAG 2 ratios).

    python3 tools/check_contrast.py

Text colors must reach 4.5:1 on the surfaces they are normally drawn on.
Status colors (accent, link, negative, ...) rarely sit on buttons or on the
alternate surfaces (striped rows), so those pairs must reach 3:1 and are
listed when they fall under 4.5. Exits with status 1 on a failure.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TEXT, LARGE = 4.5, 3.0
SURFACES = ["bg", "view", "header"]
ALT_SURFACES = ["button", "bg_alt", "view_alt"]
BODY = ["fg", "fg_muted"]
STATUS = ["accent", "link", "visited", "negative", "neutral", "positive"]
# (text, background) pairs outside the grid above
EXTRA = [("accent_fg", "accent"), ("on_negative", "negative"), ("comp_fg", "comp_bg")]


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def pairs():
    """Yield (text, background, required ratio)."""
    for fg in BODY:                       # plain and muted text: everywhere
        for bg in SURFACES + ALT_SURFACES:
            yield fg, bg, TEXT
    for fg in STATUS:
        for bg in SURFACES:
            yield fg, bg, TEXT
        for bg in ALT_SURFACES:
            yield fg, bg, LARGE
    for fg, bg in EXTRA:
        yield fg, bg, TEXT


def main():
    variants = json.loads((ROOT / "palette.json").read_text())["variants"]
    failed = 0
    for key, variant in variants.items():
        colors = variant["colors"]
        rows = [(fg, bg, need, ratio(colors[fg], colors[bg])) for fg, bg, need in pairs()]
        bad = [r for r in rows if r[3] < r[2]]
        soft = [r for r in rows if r[2] <= r[3] < TEXT]
        failed += len(bad)
        print(f"{variant['label']}: {len(rows) - len(bad)} of {len(rows)} pairs pass")
        for fg, bg, need, got in bad:
            print(f"  FAIL  {fg} on {bg}: {got:.2f} (needs {need})")
        for fg, bg, need, got in soft:
            print(f"  note  {fg} on {bg}: {got:.2f} (button or alternate surface, needs {need})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
