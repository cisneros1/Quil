#!/usr/bin/env python3
"""Give the login screen (Plasma Login Manager) Quil's look. Needs root.

    tools/login_screen.py dark        set it up for Quil Dark (or: light)
    tools/login_screen.py --remove    undo it

Run ./install.sh first: this copies the installed Quil files. Also available
as ./install.sh --login.

The login screen runs as its own user ("plasmalogin"), which can't read your
home directory, so everything it needs is copied to places it can read:

    wallpaper                           ~plasmalogin/wallpapers/Quil
    Plasma style, cursors, color scheme /usr/local/share
    Inter, if it's only installed for you   /usr/local/share/fonts/quil
    colors, fonts, cursor, Plasma style ~plasmalogin/.config (merged into what's there)
    which wallpaper to show             /etc/plasmalogin.conf

It's the same thing System Settings > Login Screen does when you pick a
wallpaper and press "Apply Plasma Settings", except that Quil's own files come
along. Pressing that button later replaces these settings with your current
ones.
"""

import configparser
import json
import os
import pwd
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GREETER_USER = "plasmalogin"
GREETER_CONF = Path("/etc/plasmalogin.conf")
SYSTEM_SHARE = Path("/usr/local/share")
WALLPAPER_GROUP = ["Greeter", "Wallpaper", "org.kde.image", "General"]


def die(msg):
    sys.exit(f"login_screen: {msg}")


def ini(path=None):
    """A KConfig file, read loosely: keys keep their case, nested groups stay "[A][B]"."""
    cp = configparser.RawConfigParser(strict=False, interpolation=None, delimiters=("=",),
                                      comment_prefixes=("#",), allow_no_value=True)
    cp.optionxform = str
    if path and Path(path).is_file():
        cp.read(path)
    return cp


def write_ini(cp, path):
    with open(path, "w") as out:
        cp.write(out, space_around_delimiters=False)


def kwriteconfig(group, key, value=None):
    cmd = ["kwriteconfig6", "--file", str(GREETER_CONF)]
    for g in group:
        cmd += ["--group", g]
    cmd += ["--key", key] + (["--delete"] if value is None else [value])
    subprocess.run(cmd, check=True)


def invoking_user():
    name = os.environ.get("SUDO_USER")
    if not name or name == "root":
        die("run this as yourself or through sudo, not from a root login")
    return pwd.getpwnam(name)


def greeter_user():
    try:
        return pwd.getpwnam(GREETER_USER)
    except KeyError:
        die(f"no '{GREETER_USER}' user: this only supports Plasma Login Manager (Plasma 6.6 or later)")


def chown_tree(path, user):
    for dirpath, _, files in os.walk(path):
        os.chown(dirpath, user.pw_uid, user.pw_gid)
        for name in files:
            os.chown(os.path.join(dirpath, name), user.pw_uid, user.pw_gid, follow_symlinks=False)


def replace_tree(src, dest):
    if dest.is_symlink():
        dest.unlink()
    shutil.rmtree(dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest, symlinks=True)


def user_only_fonts(family, home, share):
    """The font files of `family` in your home directory, unless it is also installed system-wide."""
    out = subprocess.run(["fc-list", family, "file"], capture_output=True, text=True).stdout
    listed = [Path(line.strip().rstrip(":").strip()) for line in out.splitlines() if line.strip()]
    if any(home not in f.parents for f in listed):
        return []
    found = []
    for fonts in {share / "fonts", home / ".local/share/fonts", home / ".fonts"}:
        if fonts.is_dir():
            scan = subprocess.run(["fc-scan", "--format", "%{family}|%{file}\n", str(fonts)],
                                  capture_output=True, text=True).stdout
            for line in scan.splitlines():
                families, _, file = line.partition("|")
                if family in families.split(",") and file:
                    found.append(Path(file))
    return sorted(set(found))


def settings_from(defaults, colors):
    """{config file: {group: {key: value}}} for the greeter, from the global theme's files."""
    files = {"kdeglobals": {}, "plasmarc": {}, "kcminputrc": {}}
    lnf = ini(defaults)
    for section in lnf.sections():
        name, _, group = section.partition("][")       # "kdeglobals][General"
        # not the icon theme: the greeter only gets Quil's cursors, not its icons
        if name in files and group and group != "Icons":
            files[name][group] = dict(lnf.items(section))
    scheme = ini(colors)
    for section in scheme.sections():
        files["kdeglobals"].setdefault(section, {}).update(scheme.items(section))
    return files


def setup(variant):
    user, greeter = invoking_user(), greeter_user()
    home, greeter_home = Path(user.pw_dir), Path(greeter.pw_dir)
    palette = json.loads((ROOT / "palette.json").read_text())
    meta = palette["meta"]
    if variant not in palette["variants"]:
        die(f"unknown variant '{variant}' (expected one of: {', '.join(palette['variants'])})")
    name = meta["name"]
    labels = [v["label"] for v in palette["variants"].values()]
    label = palette["variants"][variant]["label"]
    share = Path(os.environ.get("QUIL_DATA_HOME") or home / ".local/share")

    defaults = share / f"plasma/look-and-feel/{meta['id_prefix']}.{variant}/contents/defaults"
    colors = share / f"color-schemes/{name}{label}.colors"
    wallpaper = share / f"wallpapers/{name}"
    for needed in (defaults, colors, wallpaper):
        if not needed.exists():
            die(f"{needed} is missing: run ./install.sh first")

    # Wallpaper, where the login manager's own settings page puts it.
    dest = greeter_home / "wallpapers" / name
    replace_tree(wallpaper, dest)
    chown_tree(greeter_home / "wallpapers", greeter)
    print(f"installed {dest}")
    kwriteconfig(["Greeter"], "WallpaperPluginId", "org.kde.image")
    kwriteconfig(WALLPAPER_GROUP, "Image", f"file://{dest}")
    print(f"set the wallpaper in {GREETER_CONF}")

    # Theme files the greeter loads by name: both variants, so switching is cheap.
    for lab in labels:
        slug = f"{name}-{lab}"
        if (share / f"plasma/desktoptheme/{slug}").is_dir():
            replace_tree(share / f"plasma/desktoptheme/{slug}", SYSTEM_SHARE / f"plasma/desktoptheme/{slug}")
            print(f"installed {SYSTEM_SHARE}/plasma/desktoptheme/{slug}")
        icons = share / f"icons/{slug}"
        if (icons / "cursors").is_dir():       # only the cursors, not the app icons
            out = SYSTEM_SHARE / f"icons/{slug}"
            shutil.rmtree(out, ignore_errors=True)
            out.mkdir(parents=True)
            (out / "index.theme").write_text(
                f"[Icon Theme]\nName={name} {lab}\nComment={name} cursors\nInherits=breeze_cursors\n")
            for sub in ("cursors", "cursors_scalable"):
                if (icons / sub).is_dir():
                    shutil.copytree(icons / sub, out / sub, symlinks=True)
            print(f"installed {out} (cursors)")
        scheme = share / f"color-schemes/{name}{lab}.colors"
        if scheme.is_file():
            (SYSTEM_SHARE / "color-schemes").mkdir(parents=True, exist_ok=True)
            shutil.copy(scheme, SYSTEM_SHARE / "color-schemes" / scheme.name)
            print(f"installed {SYSTEM_SHARE}/color-schemes/{scheme.name}")

    # The UI font, when it only exists in your home directory.
    font_files = user_only_fonts(palette["fonts"]["ui"], home, share)
    if font_files:
        fonts = SYSTEM_SHARE / "fonts" / name.lower()
        shutil.rmtree(fonts, ignore_errors=True)
        fonts.mkdir(parents=True)
        for f in font_files:
            shutil.copy(f, fonts / f.name)
        subprocess.run(["fc-cache", "-f", str(fonts)], check=False)
        print(f"installed {fonts} ({palette['fonts']['ui']})")

    # Colors, fonts, cursor and Plasma style, merged into the greeter's settings.
    config = greeter_home / ".config"
    config.mkdir(mode=0o700, exist_ok=True)
    for filename, groups in settings_from(defaults, colors).items():
        cp = ini(config / filename)
        for group, values in groups.items():
            if not cp.has_section(group):
                cp.add_section(group)
            for key, value in values.items():
                cp.set(group, key, value)
        write_ini(cp, config / filename)
        print(f"updated {config / filename}")
    chown_tree(config, greeter)
    shutil.rmtree(greeter_home / ".cache", ignore_errors=True)   # cached Plasma style renders

    print(f"\nThe login screen will use {name} {label} the next time it starts (log out, or reboot).")


def remove():
    greeter = greeter_user()
    greeter_home = Path(greeter.pw_dir)
    palette = json.loads((ROOT / "palette.json").read_text())
    name = palette["meta"]["name"]
    labels = [v["label"] for v in palette["variants"].values()]

    wallpaper = greeter_home / "wallpapers" / name
    current = subprocess.run(["kreadconfig6", "--file", str(GREETER_CONF),
                              *(a for g in WALLPAPER_GROUP for a in ("--group", g)), "--key", "Image"],
                             capture_output=True, text=True).stdout.strip()
    if current == f"file://{wallpaper}":
        kwriteconfig(WALLPAPER_GROUP, "Image")
        print(f"removed the wallpaper setting from {GREETER_CONF}")
    paths = [wallpaper, SYSTEM_SHARE / "fonts" / name.lower()]
    for lab in labels:
        paths += [SYSTEM_SHARE / f"plasma/desktoptheme/{name}-{lab}", SYSTEM_SHARE / f"icons/{name}-{lab}",
                  SYSTEM_SHARE / f"color-schemes/{name}{lab}.colors"]
    for path in paths:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        else:
            continue
        print(f"removed {path}")

    # Take Quil back out of the greeter's settings; everything else in them stays.
    config = greeter_home / ".config"
    is_quil = lambda value: (value or "").startswith(name)   # noqa: E731
    for filename, group, key in (("plasmarc", "Theme", "name"), ("kcminputrc", "Mouse", "cursorTheme")):
        cp = ini(config / filename)
        if cp.has_option(group, key) and is_quil(cp.get(group, key)):
            cp.remove_option(group, key)
            write_ini(cp, config / filename)
            print(f"removed {key} from {config / filename}")
    cp = ini(config / "kdeglobals")
    if cp.has_option("General", "ColorScheme") and is_quil(cp.get("General", "ColorScheme")):
        for section in [s for s in cp.sections() if s.startswith(("Colors:", "ColorEffects:"))] + ["WM"]:
            cp.remove_section(section)
        for key in ("ColorScheme", "Name", "shadeSortColumn", "font", "menuFont", "toolBarFont",
                    "smallestReadableFont", "fixed", "activeFont"):
            cp.remove_option("General", key)
        write_ini(cp, config / "kdeglobals")
        print(f"removed Quil's colors and fonts from {config / 'kdeglobals'}")
    if config.is_dir():
        chown_tree(config, greeter)
    shutil.rmtree(greeter_home / ".cache", ignore_errors=True)
    print("\nThe login screen is back to its own look. To give it your current theme instead, use "
          "System Settings > Login Screen > Apply Plasma Settings.")


def main():
    args = sys.argv[1:]
    if len(args) != 1 or args[0] in ("-h", "--help"):
        sys.exit(__doc__)
    if os.geteuid() != 0:
        # Root can't see your XDG_DATA_HOME, so pass it along.
        env = ["env", f"QUIL_DATA_HOME={os.environ['XDG_DATA_HOME']}"] if os.environ.get("XDG_DATA_HOME") else []
        os.execvp("sudo", ["sudo", *env, "/usr/bin/python3", "-I", str(Path(__file__).resolve()), *args])
    if args[0] == "--remove":
        remove()
    else:
        setup(args[0])


if __name__ == "__main__":
    main()
