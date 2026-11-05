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

        Repeater {
            id: repeater

            delegate: DockItem {
                tasksModel: appsModel
                vertical: root.vertical
                thickness: root.thickness
                itemLength: root.itemLength
                iconSize: root.iconSize
            }
        }
    }
}
