/*
    One app in the Quil Dock: icon, tiny state bar, hover lift, click handling
    and context menu.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.extras as PlasmaExtras
import org.kde.kirigami as Kirigami
import org.kde.taskmanager as TaskManager

PlasmaCore.ToolTipArea {
    id: item

    required property var model
    required property int index

    property TaskManager.TasksModel tasksModel
    property bool vertical
    property real thickness
    property int itemLength
    property int iconSize

    // ----------------------------------------------------------- appearance
    readonly property int edge: Plasmoid.location          // the screen edge the dock sits on
    readonly property int liftDistance: Math.max(3, Math.round(iconSize * 0.12))
    readonly property int barThickness: 3
    readonly property int barGap: 3
    readonly property bool hasWindow: model.IsWindow || model.IsGroupParent
    readonly property color barColor: {
        if (model.IsDemandingAttention) {
            return Kirigami.Theme.neutralTextColor;
        }
        if (model.IsMinimized) {
            return Kirigami.Theme.disabledTextColor;
        }
        if (model.IsActive) {
            return Kirigami.Theme.highlightColor;
        }
        return Qt.alpha(Kirigami.Theme.highlightColor, 0.55);
    }
    readonly property int barLength: model.IsActive || model.IsDemandingAttention ? 14 : 6

    width: vertical ? thickness : itemLength
    height: vertical ? itemLength : thickness

    mainText: model.AppName || model.display || ""
    subText: hasWindow && model.display !== model.AppName ? (model.display || "") : ""
    location: Plasmoid.location
    active: menu.status !== PlasmaExtras.Menu.Open

    // Distance the icon is pushed away from the screen edge (hover lift / press dip).
    property real lift: mouse.containsMouse ? liftDistance : 0
    Behavior on lift {
        NumberAnimation { duration: Kirigami.Units.shortDuration * 1.5; easing.type: Easing.OutCubic }
    }

    // Icon + gap + bar, centered across the panel; the bar faces the screen edge.
    readonly property real stackStart: Math.round((thickness - iconSize - barGap - barThickness) / 2)

    Kirigami.Icon {
        id: icon
        width: item.iconSize
        height: item.iconSize
        source: item.model.decoration
        active: false                               // no hover glow
        roundToIconSize: false
        scale: mouse.pressed ? 0.92 : 1
        opacity: item.model.IsStartup ? startupPulse.value : 1

        x: {
            const along = Math.round((item.width - width) / 2);
            if (!item.vertical) return along;
            return item.edge === PlasmaCore.Types.LeftEdge
                ? item.stackStart + item.barThickness + item.barGap + item.lift
                : item.stackStart - item.lift;
        }
        y: {
            const along = Math.round((item.height - height) / 2);
            if (item.vertical) return along;
            return item.edge === PlasmaCore.Types.TopEdge
                ? item.stackStart + item.barThickness + item.barGap + item.lift
                : item.stackStart - item.lift;
        }

        Behavior on scale {
            NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic }
        }
    }

    QtObject {
        id: startupPulse
        property real value: 1
        property SequentialAnimation anim: SequentialAnimation {
            running: item.model.IsStartup
            loops: Animation.Infinite
            NumberAnimation { target: startupPulse; property: "value"; to: 0.45; duration: 500 }
            NumberAnimation { target: startupPulse; property: "value"; to: 1; duration: 500 }
            onStopped: startupPulse.value = 1
        }
    }

    Rectangle {
        id: bar
        visible: item.hasWindow
        radius: item.barThickness / 2
        color: item.barColor
        width: item.vertical ? item.barThickness : item.barLength
        height: item.vertical ? item.barLength : item.barThickness
        x: {
            if (!item.vertical) return Math.round((item.width - width) / 2);
            return item.edge === PlasmaCore.Types.LeftEdge
                ? item.stackStart
                : item.stackStart + item.iconSize + item.barGap;
        }
        y: {
            if (item.vertical) return Math.round((item.height - height) / 2);
            return item.edge === PlasmaCore.Types.TopEdge
                ? item.stackStart
                : item.stackStart + item.iconSize + item.barGap;
        }

        Behavior on width { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }
        Behavior on height { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }
        Behavior on color { ColorAnimation { duration: Kirigami.Units.shortDuration } }
    }

    // ------------------------------------------------------------- behavior
    function modelIndex(child) {
        return child === undefined ? tasksModel.makeModelIndex(index) : tasksModel.makeModelIndex(index, child);
    }

    function activate() {
        if (model.IsLauncher || model.IsStartup) {
            tasksModel.requestActivate(modelIndex());
            return;
        }
        if (model.IsGroupParent && model.ChildCount > 1) {
            // Cycle through the app's windows, starting with the most recent one.
            let active = -1, recent = 0, recentTime = null;
            for (let i = 0; i < model.ChildCount; ++i) {
                const child = modelIndex(i);
                if (tasksModel.data(child, TaskManager.AbstractTasksModel.IsActive)) {
                    active = i;
                }
                const t = tasksModel.data(child, TaskManager.AbstractTasksModel.LastActivated);
                if (t && (!recentTime || t > recentTime)) {
                    recentTime = t;
                    recent = i;
                }
            }
            tasksModel.requestActivate(modelIndex(active >= 0 ? (active + 1) % model.ChildCount : recent));
            return;
        }
        if (model.IsActive && !model.IsMinimized) {
            tasksModel.requestToggleMinimized(modelIndex());
        } else {
            tasksModel.requestActivate(modelIndex());
        }
    }

    // Tell KWin where this icon is, so minimize animations fly to it.
    function publishGeometry() {
        if (!hasWindow || !tasksModel) {
            return;
        }
        const p = mapToGlobal(0, 0);
        tasksModel.requestPublishDelegateGeometry(modelIndex(), Qt.rect(p.x, p.y, width, height), item);
    }

    onXChanged: geometryTimer.restart()
    onYChanged: geometryTimer.restart()
    onHasWindowChanged: geometryTimer.restart()
    Component.onCompleted: geometryTimer.restart()

    Timer {
        id: geometryTimer
        interval: 250
        onTriggered: item.publishGeometry()
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton

        onClicked: event => {
            if (event.button === Qt.LeftButton) {
                item.activate();
            } else if (event.button === Qt.MiddleButton) {
                item.tasksModel.requestNewInstance(item.modelIndex());
            } else if (event.button === Qt.RightButton) {
                menu.refresh();
                menu.openRelative();
            }
        }
    }

    // --------------------------------------------------------- context menu
    PlasmaExtras.Menu {
        id: menu
        visualParent: item
        placement: {
            switch (item.edge) {
            case PlasmaCore.Types.LeftEdge: return PlasmaExtras.Menu.RightPosedTopAlignedPopup;
            case PlasmaCore.Types.TopEdge: return PlasmaExtras.Menu.BottomPosedLeftAlignedPopup;
            case PlasmaCore.Types.RightEdge: return PlasmaExtras.Menu.LeftPosedTopAlignedPopup;
            default: return PlasmaExtras.Menu.TopPosedLeftAlignedPopup;
            }
        }

        property bool pinned: false
        readonly property string launcherUrl: item.model.LauncherUrlWithoutIcon ? item.model.LauncherUrlWithoutIcon.toString() : ""

        function refresh() {
            pinned = launcherUrl !== "" && item.tasksModel.launcherPosition(launcherUrl) !== -1;
        }

        PlasmaExtras.MenuItem {
            section: true
            text: item.mainText
        }
        PlasmaExtras.MenuItem {
            visible: item.model.CanLaunchNewInstance !== false
            text: item.hasWindow ? "Open New Window" : "Start New Instance"
            icon: "window-new"
            onClicked: item.tasksModel.requestNewInstance(item.modelIndex())
        }
        PlasmaExtras.MenuItem {
            visible: menu.launcherUrl !== ""
            text: menu.pinned ? "Unpin from Dock" : "Pin to Dock"
            icon: menu.pinned ? "window-unpin" : "window-pin"
            onClicked: {
                if (menu.pinned) {
                    item.tasksModel.requestRemoveLauncher(menu.launcherUrl);
                } else {
                    item.tasksModel.requestAddLauncher(menu.launcherUrl);
                }
            }
        }
        PlasmaExtras.MenuItem {
            separator: true
            visible: item.hasWindow
        }
        PlasmaExtras.MenuItem {
            visible: item.hasWindow && !item.model.IsGroupParent && item.model.IsMinimizable !== false
            text: item.model.IsMinimized ? "Restore" : "Minimize"
            icon: item.model.IsMinimized ? "window-restore" : "window-minimize"
            onClicked: item.tasksModel.requestToggleMinimized(item.modelIndex())
        }
        PlasmaExtras.MenuItem {
            visible: item.hasWindow
            text: item.model.IsGroupParent && item.model.ChildCount > 1 ? "Close All Windows" : "Close Window"
            icon: "window-close"
            onClicked: item.tasksModel.requestClose(item.modelIndex())
        }
    }
}
