/*
    One app in the Quil Dock: icon, tiny state bar, hover lift, click handling
    and context menu.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Window

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
    property var badges: ({})

    // Desktop file id ("org.kde.konsole.desktop"), the key apps use for badges.
    readonly property string appId: {
        if (model.StorageId) {
            return model.StorageId;
        }
        const url = model.LauncherUrlWithoutIcon ? model.LauncherUrlWithoutIcon.toString() : "";
        return url.replace(/^applications:/, "").replace(/^.*\//, "");
    }
    readonly property var badge: badges[appId] || ({})
    readonly property int unreadCount: badge["count-visible"] ? Math.max(0, badge.count || 0) : 0
    readonly property bool urgent: model.IsDemandingAttention || !!badge.urgent

    // ----------------------------------------------------------- appearance
    readonly property int edge: Plasmoid.location          // the screen edge the dock sits on
    readonly property int liftDistance: Math.max(3, Math.round(iconSize * 0.12))
    readonly property int barThickness: 3
    readonly property int barGap: 3
    readonly property bool hasWindow: model.IsWindow || model.IsGroupParent
    readonly property color barColor: {
        if (urgent) {
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
    readonly property int barLength: model.IsActive || urgent ? 14 : 6

    width: vertical ? thickness : itemLength
    height: vertical ? itemLength : thickness

    mainText: model.AppName || model.display || ""
    subText: {
        const parts = [];
        if (hasWindow && model.display !== model.AppName && model.display) {
            parts.push(model.display);
        }
        if (unreadCount > 0) {
            parts.push(unreadCount === 1 ? "1 unread" : `${unreadCount} unread`);
        }
        return parts.join(" · ");
    }
    location: Plasmoid.location
    active: menu.status !== PlasmaExtras.Menu.Open

    // Distance the icon is pushed away from the screen edge (hover lift / press dip).
    property real lift: mouse.containsMouse || mouse.dragging ? liftDistance : 0
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
        scale: mouse.dragging ? 1.08 : mouse.pressed ? 0.92 : 1
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

        // Unread-count badge, top-right corner of the icon.
        Rectangle {
            id: badgeBubble
            visible: item.unreadCount > 0
            readonly property int size: Math.max(14, Math.round(item.iconSize * 0.36))
            height: size
            width: Math.max(size, badgeLabel.implicitWidth + size * 0.55)
            radius: size / 2
            x: parent.width - width * 0.7
            y: -height * 0.3
            color: Kirigami.Theme.negativeTextColor
            border.width: 1.5
            border.color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.6)

            Text {
                id: badgeLabel
                anchors.centerIn: parent
                text: item.unreadCount > 99 ? "99+" : String(item.unreadCount)
                color: Kirigami.Theme.backgroundColor
                font.pixelSize: Math.round(badgeBubble.size * 0.62)
                font.weight: Font.Bold
            }
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
        preventStealing: dragging

        // Drag to reorder: past the drag threshold the icon follows the pointer's
        // slot, moving through the model so pinned apps keep their new order.
        property bool dragging: false
        property bool dragged: false
        property point pressPoint

        onPressed: event => {
            pressPoint = Qt.point(event.x, event.y);
            dragged = false;
        }

        onPositionChanged: event => {
            if (!(pressedButtons & Qt.LeftButton)) {
                return;
            }
            if (!dragging) {
                const distance = Math.hypot(event.x - pressPoint.x, event.y - pressPoint.y);
                if (distance < Application.styleHints.startDragDistance) {
                    return;
                }
                dragging = true;
                dragged = true;
            }
            const p = mapToItem(item.parent, event.x, event.y);
            const along = item.vertical ? p.y : p.x;
            const target = Math.max(0, Math.min(item.tasksModel.count - 1, Math.floor(along / item.itemLength)));
            if (target !== item.index) {
                item.tasksModel.move(item.index, target);
            }
        }

        onReleased: finishDrag()
        onCanceled: finishDrag()

        function finishDrag(): void {
            if (dragging) {
                dragging = false;
                item.tasksModel.syncLaunchers();   // persist the new pinned order
            }
        }

        onClicked: event => {
            if (dragged) {
                return;
            }
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
