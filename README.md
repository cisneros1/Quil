# Quil

A KDE Plasma 6 Global Theme in two variants:

- **Quil Dark**: deep black with turquoise accents
- **Quil Light**: a pale companion with deep turquoise accents

The look is based on [BlackTurq](https://github.com/HANCORE-linux/omarchy-blackturq-theme), an [Omarchy](https://omarchy.org) theme by HANCORE: its palette (`#0a0a0a` black, `#8FECD5` turquoise, `#D35F5F` red), square windows with a turquoise border on the focused window, and a turquoise particle-wave wallpaper. BlackTurq is dark-only, so Quil Light is our own derivation.

> Early work in progress. The palette, window decorations and wallpaper are first drafts.

## What's included

| Component | Installed to (`~/.local/share/…`) | Status |
|---|---|---|
| Color schemes | `color-schemes/QuilDark.colors`, `QuilLight.colors` | ✅ draft palette |
| Plasma style | `plasma/desktoptheme/Quil-Dark`, `Quil-Light` | 🟡 glass panel + task manager; other SVGs fall back to Breeze |
| Window decorations (Aurorae) | `aurorae/themes/Quil-Dark`, `Quil-Light` | ✅ square frame, 2px turquoise border when focused |
| Icon themes | `icons/Quil-Dark`, `Quil-Light` | ✅ Breeze plus rounded-square copies of your dock's app icons |
| Quil Dock widget | `plasma/plasmoids/com.github.cisneros1.quil.dock` | ✅ dock task manager: tiny state bars, hover lift, no hover glow |
| Wallpaper | `wallpapers/Quil` (light + `images_dark`) | ✅ particle wave, generated from SVG |
| Splash screen | inside the global theme | ✅ |
| Panel layout | inside the global theme | 🟡 Plasma default for now |
| Global themes | `plasma/look-and-feel/com.github.cisneros1.quil.{dark,light}` | ✅ |

Application style and cursors use Breeze. Icons are Breeze, except that `tools/round_icons.py` (run by `install.sh`) adds rounded-square copies of the icons of every app pinned in your Task Manager. After pinning a new app, run `python3 tools/round_icons.py` again (or `tools/round_icons.py <desktop-file-id>` for any other app).

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
  icons/                icon theme index (icons are generated on install)
  plasmoid/             Quil Dock widget (QML)
  helper/               quil-badges relay for unread counts
  dbus-services/        D-Bus activation file for the relay
  wallpaper/            wallpaper SVG, rendered to PNG at build time
tools/build.py          template renderer
tools/gen_plasma_style.py  generates the panel and task manager SVG templates
tools/round_icons.py    rounds the icons of pinned apps into the Quil icon themes
install.sh / uninstall.sh
```

Templates use `{{token}}` placeholders, in file contents and in file names:

| Token | Example output |
|---|---|
| `{{accent}}` | `#8fecd5`, any color from `palette.json` |
| `{{accent.rgb}}` | `143,236,213`, the format `.colors` and Aurorae rc files use |
| `{{full_name}}`, `{{slug}}`, `{{scheme}}`, `{{lnf_id}}` | `Quil Dark`, `Quil-Dark`, `QuilDark`, `com.github.cisneros1.quil.dark` |

Unknown tokens fail the build, and both variants must define the same set of colors.

### Quil Dock

Plasma's Task Manager brightens icons on hover and can't animate them, so Quil ships its own dock widget, **Quil Dock**. It uses KDE's public `org.kde.taskmanager` API with the same behavior as the Icons-Only Task Manager: pinned apps turn into their windows, and windows are grouped by app.

- Click opens an app, switches to it, or minimizes it if it's already active. With several windows, each click cycles through them.
- Middle-click opens a new window.
- Right-click to pin/unpin, minimize/restore or close.
- Hovering lifts the icon slightly. A tiny bar shows the state: dim turquoise (open), bright and longer (active), gray (minimized), orange (needs attention).
- Drag an icon to reorder the dock; pinned apps keep their new order.
- Apps that publish unread counts (the Unity LauncherEntry API, used by most chat and mail apps) get a red badge. QML can't listen to those D-Bus signals directly, so `install.sh` sets up a small relay, `quil-badges.service` (a systemd user service running `src/helper/quil-badges.py`). Like Plasma's own Task Manager, it also claims the `com.canonical.Unity` bus name, because some apps only send badges when that name is present.

To use it, add **Quil Dock** to a panel, or right-click your Task Manager → *Show Alternatives* → *Quil Dock*. Not yet supported: hover window previews.

### Dock tips

If you use Plasma's own Task Manager instead of Quil Dock: its indicator is sized for a 70px-tall dock (`TASK_WIDTH` in `tools/gen_plasma_style.py` is the measured button width). If you resize the dock, update `TASK_WIDTH` and regenerate so the bar stays tiny.

### Development loop

1. Edit `palette.json` or a template in `src/`.
2. Run `./install.sh --apply dark` (or `light`).
3. Some pieces need a refresh before they show the change:
   - Window decorations: `qdbus6 org.kde.KWin /KWin reconfigure`
   - Plasma style: `systemctl --user restart plasma-plasmashell`
   - Splash screen: *System Settings → Splash Screen → Quil … → Preview*

## Roadmap

- [ ] Finalize the palette (contrast check for both variants)
- [x] Glass panel and task manager (tiny running-app bar right under each icon, no hover background)
- [x] Rounded app icons for pinned apps
- [x] Quil Dock widget (hover lift, no glow)
- [x] Quil Dock: drag to reorder, unread badges
- [ ] Quil Dock: window previews
- [ ] Plasma style SVGs: widget backgrounds, dialogs, tooltips
- [ ] Panel shadow for the floating dock
- [ ] Window shadows and decoration polish
- [ ] Custom panel layout
- [ ] Real screenshots for the theme previews
- [ ] SDDM login theme and lock screen
- [ ] Publish to the KDE Store

## Credits

Colors and visual direction from [BlackTurq](https://github.com/HANCORE-linux/omarchy-blackturq-theme) by HANCORE (MIT License). No BlackTurq artwork is included; Quil's wallpaper is generated from its own SVG.

## License

[GPL-3.0-or-later](LICENSE)
