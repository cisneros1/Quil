/*
    Quil Dock: a dock-style task manager.

    Shows pinned apps and open windows (grouped by app) with a tiny state bar,
    no hover glow, and a gentle lift on hover. Built on KDE's public
    org.kde.taskmanager QML API, configured like the stock Icons-Only Task Manager.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts

import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami
import org.kde.taskmanager as TaskManager
import org.kde.plasma.workspace.dbus as DBus

PlasmoidItem {
    id: root

    readonly property bool vertical: Plasmoid.formFactor === PlasmaCore.Types.Vertical
    // Thickness available to each item, across the panel.
    readonly property real thickness: vertical ? width : height
    readonly property int iconSize: Math.max(Kirigami.Units.iconSizes.small,
                                             Math.round(thickness - barSpace - 2 * Math.max(2, thickness * 0.06)))
    readonly property int barSpace: 6                     // gap + bar thickness
    readonly property int itemLength: iconSize + Math.round(Math.max(8, thickness * 0.28))
    readonly property real contentLength: Math.max(itemLength, repeater.count * itemLength)

    preferredRepresentation: fullRepresentation

    Layout.fillWidth: false
    Layout.fillHeight: false
    Layout.minimumWidth: vertical ? 0 : contentLength
    Layout.preferredWidth: vertical ? -1 : contentLength
    Layout.maximumWidth: vertical ? -1 : contentLength
    Layout.minimumHeight: vertical ? contentLength : 0
    Layout.preferredHeight: vertical ? contentLength : -1
    Layout.maximumHeight: vertical ? contentLength : -1

    // ------------------------------------------------------------------ badges
    // Unread counts come from the quil-badges relay (src/helper/quil-badges.py),
    // which collects the apps' Unity LauncherEntry updates. Keyed by desktop file id.
    readonly property string badgeService: "com.github.cisneros1.Quil.Badges"
    readonly property string badgePath: "/com/github/cisneros1/Quil/Badges"
    property var badges: ({})

    function setBadge(id: string, props: var): void {
        const next = Object.assign({}, badges);
        if (props && Object.keys(props).length > 0) {
            next[id] = props;
        } else {
            delete next[id];
        }
        badges = next;
    }

    function loadBadges(): void {
        const reply = DBus.SessionBus.asyncCall({service: badgeService, path: badgePath, iface: badgeService,
                                                member: "GetAll", arguments: []});
        reply.finished.connect(() => {
            if (!reply.isError && reply.value) {
                root.badges = reply.value;
            }
        });
    }

    DBus.SignalWatcher {
        busType: DBus.BusType.Session
        service: root.badgeService
        path: root.badgePath
        iface: root.badgeService

        function dbusChanged(id: string, props: var): void {
            root.setBadge(id, props);
        }
    }

    DBus.DBusServiceWatcher {
        busType: DBus.BusType.Session
        watchedService: root.badgeService
        onRegisteredChanged: registered ? root.loadBadges() : (root.badges = ({}))
    }

    Component.onCompleted: loadBadges()   // also D-Bus-activates the relay if it isn't running

    TaskManager.VirtualDesktopInfo { id: virtualDesktopInfo }
    TaskManager.ActivityInfo { id: activityInfo }

    TaskManager.TasksModel {
        id: appsModel

        screenGeometry: Plasmoid.containment.screenGeometry
        activity: activityInfo.currentActivity

        filterByCurrentVirtualDesktop: true
        filterByActivity: true
        filterByScreen: false

        // Icons-only dock behavior: a pinned app's icon turns into its window.
        hideActivatedLaunchers: true
        sortMode: TaskManager.TasksModel.SortManual
        launchInPlace: true
        separateLaunchers: false
        groupMode: TaskManager.TasksModel.GroupApplications
        groupInline: false

        onLauncherListChanged: Plasmoid.configuration.launchers = launcherList

        Component.onCompleted: {
            launcherList = Plasmoid.configuration.launchers;
            repeater.model = appsModel;   // hook up the view after the initial churn
        }
    }

    Grid {
        id: grid
        anchors.centerIn: parent
        rows: root.vertical ? -1 : 1
        columns: root.vertical ? 1 : -1

        // Slide neighbors out of the way while an icon is dragged.
        move: Transition {
            NumberAnimation { properties: "x,y"; duration: Kirigami.Units.longDuration; easing.type: Easing.OutCubic }
        }

        Repeater {
            id: repeater

            delegate: DockItem {
                tasksModel: appsModel
                vertical: root.vertical
                thickness: root.thickness
                itemLength: root.itemLength
                iconSize: root.iconSize
                badges: root.badges
            }
        }
    }
}
