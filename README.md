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
| Plasma style | `plasma/desktoptheme/Quil-Dark`, `Quil-Light` | 🟡 glass panel, task manager, rounded glass popups and tooltips with soft shadows; other SVGs fall back to Breeze |
| Window decorations (Aurorae) | `aurorae/themes/Quil-Dark`, `Quil-Light` | ✅ square frame, 2px turquoise border when focused, soft shadow, translucent blurred title bar |
| Icon themes | `icons/Quil-Dark`, `Quil-Light` | ✅ [Colloid](https://github.com/vinceliuice/Colloid-icon-theme) (teal) plus rounded-square copies of your dock's app icons |
| Cursors | inside the icon themes (`cursors`, `cursors_scalable`) | ✅ Breeze's shapes in Quil's colors: dark with a turquoise edge (Dark), turquoise with a white edge (Light) |
| Quil Dock widget | `plasma/plasmoids/com.github.cisneros1.quil.dock` | ✅ dock task manager: tiny state bars, hover lift, no hover glow |
| Wallpaper | `wallpapers/Quil` (light + `images_dark`) | ✅ particle wave, generated from SVG |
| Splash screen | inside the global theme | ✅ |
| Application style | set by the global theme | 🟡 Darkly with translucent menus, toolbars and Dolphin if installed, else Breeze |
| Konsole | `konsole/Quil-Dark.profile`, `Quil-Light.profile` (+ color schemes) | ✅ Quil colors, 80% opaque with blur, JetBrains Mono; default profile |
| Syntax highlighting | `org.kde.syntax-highlighting/themes/Quil-Dark.theme`, `Quil-Light.theme` | ✅ Kate, KWrite and other KTextEditor apps; default theme in Kate and KWrite |
| Lock screen | nothing to install | ✅ follows the global theme: Quil's wallpaper, colors and font |
| Login screen | system files, see below | 🟡 opt-in (`--login`, needs sudo), Plasma Login Manager only |
| Translucent System Settings | KWin window rule + effect settings | 🟡 needs Better Blur DX |
| Fonts | set by the global theme | ✅ Inter (UI), Inter SemiBold (window titles), JetBrains Mono (fixed width) |
| Panel layout | inside the global theme | 🟡 Plasma default for now |
| Global themes | `plasma/look-and-feel/com.github.cisneros1.quil.{dark,light}` | ✅ |

The application style is [Darkly](https://github.com/Bali10050/Darkly) when it's installed (`paru -S darkly-bin`, then re-run `./install.sh`), for macOS-like menus: rounded, translucent and blurred, with roomier items, in Quil's colors. Quil's Darkly settings go to `~/.config/kdedefaults/darklyrc` ([`src/kdedefaults/darklyrc`](src/kdedefaults/darklyrc)), so changes made in Darkly's own settings still win. Darkly also makes toolbars, tab bars, menu bars and Dolphin's file view and sidebar 75% opaque. Without Darkly, apps use Breeze.

System Settings, Info Center, Discover and Plasma's own settings windows (Desktop Folder Settings, widget settings) paint their own solid backgrounds, which no app style can change. If the [Better Blur DX](https://github.com/xarblu/kwin-effects-better-blur-dx) KWin effect is installed (`paru -S kwin-effects-better-blur-dx`), `install.sh` swaps it in for KWin's own blur (same strength, plus blurred title bars), forces blur behind those apps, and adds a window rule (`quil-translucent-system-apps` in `~/.config/kwinrulesrc`) that makes them 90% opaque (`APP_OPACITY`). Edit the list in `TRANSLUCENT_APPS` in `install.sh`. Better Blur DX is built against one exact KWin version, so after a Plasma update rebuild it (`paru -S kwin-effects-better-blur-dx`) if blur disappears. Konsole gets Quil's profile as its default (`~/.config/kdedefaults/konsolerc`), so choosing another default in Konsole still wins. Its colors are the `term_*` entries in `palette.json`. Kate and KWrite get Quil's syntax colors the same way (`~/.config/kdedefaults/katerc` and `kwriterc`); other KTextEditor apps list **Quil Dark** and **Quil Light** under *Settings → Configure → Color Themes*.

The cursors are Breeze's, recolored at build time by `tools/gen_cursors.py` (colors: `cursor` and `cursor_outline` in `palette.json`). They live inside the Quil icon themes, so the cursor theme is also called **Quil Dark** / **Quil Light**. Without Breeze's SVG cursors installed, Quil keeps the Breeze cursors.

### Lock and login screens

The lock screen needs no setup: with Quil applied it shows Quil's wallpaper, colors and font, unless you picked a lock screen wallpaper of your own in *System Settings → Screen Locking*.

The login screen runs as its own user and can't read your home directory, so theming it is opt-in and needs root: `./install.sh --apply dark --login` (or `tools/login_screen.py dark` after an install). It copies Quil's wallpaper, Plasma style, cursors and font to system locations and merges Quil's colors into the login screen's own settings; the top of [`tools/login_screen.py`](tools/login_screen.py) lists every path. `tools/login_screen.py --remove` undoes it. This supports Plasma Login Manager (Plasma 6.6 and later), not SDDM.

Icons are [Colloid](https://github.com/vinceliuice/Colloid-icon-theme) in its teal variant (`Colloid-Teal-Dark`, `Colloid-Teal-Light`), whose teal folders match Quil's accent. The fonts are [Inter](https://rsms.me/inter/) and [JetBrains Mono](https://www.jetbrains.com/lp/mono/). `install.sh` downloads the icons and fonts into `~/.local/share` if they aren't installed yet (`tools/fetch_deps.sh`), and `uninstall.sh` leaves them in place. Change them in [`palette.json`](palette.json) (`icons` per variant, and the `fonts` block).

On top of Colloid, `tools/round_icons.py` (run by `install.sh`) adds rounded-square copies of the icons of every app pinned in your Task Manager. After pinning a new app, run `python3 tools/round_icons.py` again (or `tools/round_icons.py <desktop-file-id>` for any other app).

## Install

Requires Plasma 6, `python3`, `rsvg-convert` (librsvg), `magick` (ImageMagick), `curl` and `fc-list` (fontconfig).

```sh
./install.sh                 # build and install both variants
./install.sh --apply dark    # also switch to Quil Dark (or: light)
./install.sh --apply dark --reset-layout   # also apply Quil's panel layout
./install.sh --apply dark --login          # also theme the login screen (needs sudo)
./uninstall.sh               # remove every Quil package
```

Or install, then pick **Quil Dark** or **Quil Light** in *System Settings → Colors & Themes → Global Theme*.

## How it's built

Every color lives in **[`palette.json`](palette.json)**. The files in `src/` are templates, and `tools/build.py` renders them once per variant into `build/share/`, which mirrors `~/.local/share`.

```
palette.json            all colors, fonts, icon themes and metadata, one block per variant
src/
  color-schemes/        KDE .colors template
  desktoptheme/         Plasma style (add widgets/*.svg here to override Breeze)
  aurorae/              window decoration: frame, buttons, layout rc
  syntax/               syntax highlighting theme for Kate and KWrite
  look-and-feel/        global theme: defaults, panel layout, splash
  icons/                icon theme index (icons are generated on install)
  plasmoid/             Quil Dock widget (QML)
  helper/               quil-badges relay for unread counts
  dbus-services/        D-Bus activation file for the relay
  wallpaper/            wallpaper SVG, rendered to PNG at build time
tools/build.py          template renderer
tools/gen_plasma_style.py  generates the panel, task manager, popup and tooltip SVG templates
tools/gen_aurorae.py    generates the window frame SVG template (border, shadow)
tools/gen_cursors.py    recolors Breeze's cursors into the Quil icon themes (run by build.py)
tools/check_contrast.py checks the text colors in palette.json against WCAG contrast ratios
tools/login_screen.py   themes the login screen (needs sudo)
tools/round_icons.py    rounds the icons of pinned apps into the Quil icon themes
tools/fetch_deps.sh     downloads the Colloid icons and the fonts if they're missing
install.sh / uninstall.sh
```

Templates use `{{token}}` placeholders, in file contents and in file names:

| Token | Example output |
|---|---|
| `{{accent}}` | `#8fecd5`, any color from `palette.json` |
| `{{accent.rgb}}` | `143,236,213`, the format `.colors` and Aurorae rc files use |
| `{{accent 30% on view}}` | `#2e4c45`, two palette colors mixed (30% accent, 70% view) |
| `{{full_name}}`, `{{slug}}`, `{{scheme}}`, `{{lnf_id}}` | `Quil Dark`, `Quil-Dark`, `QuilDark`, `com.github.cisneros1.quil.dark` |
| `{{font}}`, `{{font_small}}`, `{{font_title}}`, `{{font_fixed}}` | `Inter,10,-1,5,400,0,0,0,0,0,0,0,0,0,0,1` (kdeglobals font format) |
| `{{shadow_opacity}}` | `0.55`, the window shadow strength, set per variant in `palette.json` |

Unknown tokens fail the build, and both variants must define the same set of colors.

### Quil Dock

Plasma's Task Manager brightens icons on hover and can't animate them, so Quil ships its own dock widget, **Quil Dock**. It uses KDE's public `org.kde.taskmanager` API with the same behavior as the Icons-Only Task Manager: pinned apps turn into their windows, and windows are grouped by app.

- Click opens an app, switches to it, or minimizes it if it's already active. With several windows, each click cycles through them.
- Middle-click opens a new window.
- Right-click to pin/unpin, minimize/restore or close.
- Hovering lifts the icon slightly. A tiny bar shows the state: dim turquoise (open), bright and longer (active), gray (minimized), orange (needs attention).
- Drag an icon to reorder the dock; pinned apps keep their new order.
- Hovering an open app shows a live preview of each of its windows (Wayland). Click a preview to switch to that window; middle-click it or use its × to close it.
- Apps that publish unread counts (the Unity LauncherEntry API, used by most chat and mail apps) get a red badge. QML can't listen to those D-Bus signals directly, so `install.sh` sets up a small relay, `quil-badges.service` (a systemd user service running `src/helper/quil-badges.py`). Like Plasma's own Task Manager, it also claims the `com.canonical.Unity` bus name, because some apps only send badges when that name is present.

To use it, add **Quil Dock** to a panel, or right-click your Task Manager → *Show Alternatives* → *Quil Dock*.

### Dock tips

For a see-through dock, set its panel's **Opacity** to *Translucent* (right-click the dock → *Show Panel Configuration*). The default, *Adaptive*, turns the dock solid whenever a window touches it. `install.sh` also lowers KWin's blur strength to 2 (`BLUR_STRENGTH` in `install.sh`), so the wallpaper shows through the glass instead of blurring into one flat color. It's written to `~/.config/kdedefaults/kwinrc`, so the slider in *System Settings → Desktop Effects → Blur* still overrides it.

If you use Plasma's own Task Manager instead of Quil Dock: its indicator is sized for a 70px-tall dock (`TASK_WIDTH` in `tools/gen_plasma_style.py` is the measured button width). If you resize the dock, update `TASK_WIDTH` and regenerate so the bar stays tiny.

### Development loop

1. Edit `palette.json` or a template in `src/`.
2. After a palette change, run `python3 tools/check_contrast.py`. It fails when a text color drops under 4.5:1 on the surfaces it's used on.
3. Run `./install.sh --apply dark` (or `light`).
4. Some pieces need a refresh before they show the change:
   - Window decorations: `--apply` already reloads KWin; without it, `qdbus6 org.kde.KWin /KWin reconfigure`
   - Plasma style: `systemctl --user restart plasma-plasmashell`
   - Splash screen: *System Settings → Splash Screen → Quil … → Preview*

## Roadmap

- [x] Finalize the palette (contrast check for both variants)
- [x] Glass panel and task manager (tiny running-app bar right under each icon, no hover background)
- [x] Rounded app icons for pinned apps
- [x] Colloid icons and Inter / JetBrains Mono fonts
- [x] Quil Dock widget (hover lift, no glow)
- [x] Quil Dock: drag to reorder, unread badges
- [ ] Quil Dock: window previews
- [x] Plasma style: rounded glass popups and tooltips (launcher, system tray, calendar, notifications)
- [ ] Plasma style SVGs: desktop widget backgrounds
- [ ] Panel shadow for the floating dock
- [x] Window shadows and a clearer border on unfocused windows
- [x] Cursors, syntax highlighting for Kate and KWrite
- [ ] Custom panel layout
- [ ] Real screenshots for the theme previews
- [x] Lock screen (follows the global theme) and login screen (Plasma Login Manager, opt-in)
- [ ] SDDM login theme
- [ ] Publish to the KDE Store

## Credits

Colors and visual direction from [BlackTurq](https://github.com/HANCORE-linux/omarchy-blackturq-theme) by HANCORE (MIT License). No BlackTurq artwork is included; Quil's wallpaper is generated from its own SVG.

The cursors are KDE's [Breeze](https://invent.kde.org/plasma/breeze) cursors, recolored on your machine from the copy your distribution installs. None of them are in this repository.

## License

[GPL-3.0-or-later](LICENSE)
