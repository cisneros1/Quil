#!/usr/bin/env python3
"""Quil badge relay: unread counts for Quil Dock.

Apps publish unread counts and progress with the Unity LauncherEntry D-Bus API:
an `Update(app_uri, properties)` signal sent from any object path. QML can't
listen to signals from arbitrary senders, so this small service collects them
and re-publishes them from one fixed name that Quil Dock watches:

    name/interface  com.github.cisneros1.Quil.Badges
    path            /com/github/cisneros1/Quil/Badges
    GetAll() -> a{sa{sv}}               current state, keyed by desktop file id
    signal Changed(s id, a{sv} props)   props is empty when the app goes away

It also claims com.canonical.Unity (as Plasma's Task Manager does), since some
apps only send badges when a Unity-compatible launcher is running.

Run by the quil-badges systemd user service (installed by install.sh).
"""

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

NAME = "com.github.cisneros1.Quil.Badges"
PATH = "/com/github/cisneros1/Quil/Badges"
IFACE = NAME
INTROSPECTION = """
<node>
  <interface name="%s">
    <method name="GetAll"><arg type="a{sa{sv}}" name="badges" direction="out"/></method>
    <signal name="Changed"><arg type="s" name="id"/><arg type="a{sv}" name="properties"/></signal>
  </interface>
</node>
""" % IFACE
# Unity LauncherEntry properties we relay, and how to normalize them.
PROPS = {
    "count": ("x", int),
    "count-visible": ("b", bool),
    "progress": ("d", float),
    "progress-visible": ("b", bool),
    "urgent": ("b", bool),
}

entries = {}   # desktop file id -> {property: value}
senders = {}   # D-Bus unique name -> set of desktop file ids it updated


def app_id(uri):
    return uri.removeprefix("application://")


def as_variants(props):
    return {k: GLib.Variant(PROPS[k][0], v) for k, v in props.items()}


def emit(conn, app, props):
    conn.emit_signal(None, PATH, IFACE, "Changed", GLib.Variant("(sa{sv})", (app, as_variants(props))))


def on_update(conn, sender, path, iface, signal, params, _data):
    uri, props = params.unpack()
    if not uri:
        return
    app = app_id(uri)
    entry = entries.setdefault(app, {})
    for key, value in props.items():
        if key in PROPS:
            try:
                entry[key] = PROPS[key][1](value)
            except (TypeError, ValueError):
                pass
    senders.setdefault(sender, set()).add(app)
    emit(conn, app, entry)


def on_name_owner_changed(conn, sender, path, iface, signal, params, _data):
    name, _old, new = params.unpack()
    if new or name not in senders:
        return
    for app in senders.pop(name):
        if entries.pop(app, None) is not None:
            emit(conn, app, {})


def on_method(conn, sender, path, iface, method, params, invocation):
    if method == "GetAll":
        state = {app: as_variants(props) for app, props in entries.items()}
        invocation.return_value(GLib.Variant("(a{sa{sv}})", (state,)))
    else:
        invocation.return_dbus_error("org.freedesktop.DBus.Error.UnknownMethod", method)


def main():
    conn = Gio.bus_get_sync(Gio.BusType.SESSION)
    node = Gio.DBusNodeInfo.new_for_xml(INTROSPECTION)
    conn.register_object(PATH, node.interfaces[0], on_method, None, None)

    conn.signal_subscribe(None, "com.canonical.Unity.LauncherEntry", "Update", None, None,
                          Gio.DBusSignalFlags.NONE, on_update, None)
    conn.signal_subscribe("org.freedesktop.DBus", "org.freedesktop.DBus", "NameOwnerChanged",
                          "/org/freedesktop/DBus", None, Gio.DBusSignalFlags.NONE, on_name_owner_changed, None)

    loop = GLib.MainLoop()
    Gio.bus_own_name_on_connection(conn, NAME, Gio.BusNameOwnerFlags.NONE, None,
                                   lambda *_: loop.quit())
    Gio.bus_own_name_on_connection(conn, "com.canonical.Unity", Gio.BusNameOwnerFlags.NONE, None, None)
    loop.run()


if __name__ == "__main__":
    main()
