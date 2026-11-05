# Quil

A KDE Plasma 6 Global Theme in two variants:

- **Quil Dark**: ink-black surfaces with gold-ink accents
- **Quil Light**: warm parchment surfaces with sepia-ink accents

> Early work in progress. The palette, window decorations and wallpaper are first drafts.

## What's included

| Component | Installed to (`~/.local/share/…`) | Status |
|---|---|---|
| Color schemes | `color-schemes/QuilDark.colors`, `QuilLight.colors` | ✅ draft palette |
| Plasma style | `plasma/desktoptheme/Quil-Dark`, `Quil-Light` | 🟡 colors only; SVGs fall back to Breeze |
| Window decorations (Aurorae) | `aurorae/themes/Quil-Dark`, `Quil-Light` | ✅ flat titlebar with rounded top corners |
| Wallpaper | `wallpapers/Quil` (light + `images_dark`) | ✅ generated from SVG |
| Splash screen | inside the global theme | ✅ |
| Panel layout | inside the global theme | 🟡 Plasma default for now |
| Global themes | `plasma/look-and-feel/com.github.cisneros1.quil.{dark,light}` | ✅ |

Application style, icons and cursors use Breeze.

## Install

Requires Plasma 6, `python3`, `rsvg-convert` (librsvg) and `magick` (ImageMagick).

```sh
./install.sh                 # build and install both variants
./install.sh --apply dark    # also switch to Quil Dark (or: light)
./install.sh --apply dark --reset-layout   # also apply Quil's panel layout
./uninstall.sh               # remove every Quil package
```

Or install, then pick **Quil Dark** or **Quil Light** in *System Settings → Colors & Themes → Global Theme*.

## How it's built

Every color lives in **[`palette.json`](palette.json)**. The files in `src/` are templates, and `tools/build.py` renders them once per variant into `build/share/`, which mirrors `~/.local/share`.

```
palette.json            all colors and metadata, one block per variant
src/
  color-schemes/        KDE .colors template
  desktoptheme/         Plasma style (add widgets/*.svg here to override Breeze)
  aurorae/              window decoration: frame, buttons, layout rc
  look-and-feel/        global theme: defaults, panel layout, splash
  wallpaper/            wallpaper SVG, rendered to PNG at build time
tools/build.py          template renderer
install.sh / uninstall.sh
```

Templates use `{{token}}` placeholders, in file contents and in file names:

| Token | Example output |
|---|---|
| `{{accent}}` | `#d6a65c`, any color from `palette.json` |
| `{{accent.rgb}}` | `214,166,92`, the format `.colors` and Aurorae rc files use |
| `{{full_name}}`, `{{slug}}`, `{{scheme}}`, `{{lnf_id}}` | `Quil Dark`, `Quil-Dark`, `QuilDark`, `com.github.cisneros1.quil.dark` |

Unknown tokens fail the build, and both variants must define the same set of colors.

### Development loop

1. Edit `palette.json` or a template in `src/`.
2. Run `./install.sh --apply dark` (or `light`).
3. Some pieces need a refresh before they show the change:
   - Window decorations: `qdbus6 org.kde.KWin /KWin reconfigure`
   - Plasma style: `systemctl --user restart plasma-plasmashell`
   - Splash screen: *System Settings → Splash Screen → Quil … → Preview*

## Roadmap

- [ ] Finalize the palette (contrast check for both variants)
- [ ] Plasma style SVGs: panel, widget backgrounds, dialogs, tooltips
- [ ] Window shadows and decoration polish
- [ ] Custom panel layout
- [ ] Real screenshots for the theme previews
- [ ] SDDM login theme and lock screen
- [ ] Publish to the KDE Store

## License

[GPL-3.0-or-later](LICENSE)
