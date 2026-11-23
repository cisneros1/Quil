/*
    Hover tooltip for a Quil Dock item with open windows: the app name, then a
    live thumbnail of each window. Click a thumbnail to switch to that window,
    middle-click (or the x button) to close it.

    Thumbnails are KWin screencasts (Wayland), requested only while the tooltip
    is on screen.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import QtQml.Models

import org.kde.plasma.components as PlasmaComponents
import org.kde.kirigami as Kirigami
import org.kde.taskmanager as TaskManager
import org.kde.pipewire as PipeWire

Item {
    id: previews

    property TaskManager.TasksModel tasksModel
    property int taskIndex: -1          // row of the dock item in tasksModel
    property bool isGroup: false        // several windows, grouped under one item
    property var task                   // the dock item's own model (single window)
    property string title
    property string subtitle
    property bool streaming: false      // tooltip is showing: run the screencasts
    property real maxWidth: 1600

    signal done()                       // a window was activated or closed

    readonly property real spacing: Kirigami.Units.largeSpacing
    readonly property int windowCount: isGroup ? groupModel.count : 1
    // Shrink the cards when many windows wouldn't fit side by side.
    readonly property real cardWidth: Math.min(Kirigami.Units.gridUnit * 13,
                                               (maxWidth - spacing * (windowCount + 1)) / Math.max(1, windowCount))
    readonly property real thumbHeight: Math.round(cardWidth * 9 / 16)

    implicitWidth: Math.max(cards.implicitWidth, header.implicitWidth) + 2 * Kirigami.Units.smallSpacing
    implicitHeight: header.implicitHeight + Kirigami.Units.smallSpacing + cards.implicitHeight + 2 * Kirigami.Units.smallSpacing

    function childIndex(row: int): var {
        return isGroup ? tasksModel.makeModelIndex(taskIndex, row) : tasksModel.makeModelIndex(taskIndex);
    }

    DelegateModel {
        id: groupModel
        model: previews.isGroup ? previews.tasksModel : null
        rootIndex: previews.tasksModel ? previews.tasksModel.makeModelIndex(previews.taskIndex) : null
        delegate: WindowCard {
            required property var model
            required property int index
            win: model
            row: index
        }
    }

    ColumnLayout {
        id: header
        x: Kirigami.Units.smallSpacing
        y: Kirigami.Units.smallSpacing
        width: previews.width - 2 * Kirigami.Units.smallSpacing
        spacing: 0

        Kirigami.Heading {
            Layout.fillWidth: true
            level: 4
            text: previews.title
            elide: Text.ElideRight
            textFormat: Text.PlainText
        }
        PlasmaComponents.Label {
            Layout.fillWidth: true
            visible: text !== ""
            text: previews.subtitle
            opacity: 0.7
            elide: Text.ElideRight
            textFormat: Text.PlainText
        }
    }

    Row {
        id: cards
        x: Kirigami.Units.smallSpacing
        y: header.y + header.height + Kirigami.Units.smallSpacing
        spacing: previews.spacing

        Repeater {
            model: previews.isGroup ? groupModel : null
        }
        WindowCard {
            visible: !previews.isGroup
            win: previews.task ?? ({})
            row: 0
        }
    }

    component WindowCard: Item {
        id: card

        property var win: ({})     // this window's model roles
        property int row: 0        // child row within the group
        readonly property string winId: win.WinIdList && win.WinIdList.length > 0 ? String(win.WinIdList[0]) : ""
        readonly property bool minimized: !!win.IsMinimized

        width: previews.cardWidth
        height: previews.thumbHeight + label.height + Kirigami.Units.smallSpacing

        // Hover / active highlight behind the card.
        Rectangle {
            anchors.fill: parent
            anchors.margins: -Kirigami.Units.smallSpacing
            radius: Kirigami.Units.cornerRadius
            color: Kirigami.Theme.highlightColor
            opacity: area.containsMouse ? 0.22 : card.win.IsActive ? 0.1 : 0
            Behavior on opacity { NumberAnimation { duration: Kirigami.Units.shortDuration } }
        }

        Item {
            id: thumbBox
            width: parent.width
            height: previews.thumbHeight

            // Fallback while the stream starts, or when there is none.
            Kirigami.Icon {
                anchors.centerIn: parent
                width: Kirigami.Units.iconSizes.large
                height: width
                source: card.win.decoration ?? ""
                visible: !(stream.item && stream.item.ready)
                opacity: card.minimized ? 0.5 : 1
            }

            Loader {
                id: stream
                anchors.fill: parent
                active: previews.streaming && card.winId !== ""
                sourceComponent: PipeWire.PipeWireSourceItem {
                    // Must stay visible: KPipeWire pauses hidden streams, so it would
                    // never become ready. It paints nothing until the first frame.
                    nodeId: request.nodeId
                    opacity: card.minimized ? 0.6 : 1

                    TaskManager.ScreencastingRequest {
                        id: request
                        uuid: card.winId
                    }
                }
            }
        }

        RowLayout {
            id: label
            anchors.top: thumbBox.bottom
            anchors.topMargin: Kirigami.Units.smallSpacing
            width: parent.width
            spacing: Kirigami.Units.smallSpacing

            PlasmaComponents.Label {
                Layout.fillWidth: true
                text: card.win.display ?? ""
                elide: Text.ElideRight
                textFormat: Text.PlainText
                opacity: card.minimized ? 0.6 : 1
            }
            PlasmaComponents.ToolButton {
                Layout.preferredWidth: Kirigami.Units.iconSizes.small + Kirigami.Units.smallSpacing * 2
                Layout.preferredHeight: Layout.preferredWidth
                icon.name: "window-close"
                flat: true
                opacity: area.containsMouse || hovered ? 1 : 0
                onClicked: {
                    previews.tasksModel.requestClose(previews.childIndex(card.row));
                    if (previews.windowCount <= 1) {
                        previews.done();
                    }
                }
            }
        }

        MouseArea {
            id: area
            anchors.fill: thumbBox
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.MiddleButton
            onClicked: event => {
                const idx = previews.childIndex(card.row);
                if (event.button === Qt.MiddleButton) {
                    previews.tasksModel.requestClose(idx);
                    if (previews.windowCount <= 1) {
                        previews.done();
                    }
                } else {
                    previews.tasksModel.requestActivate(idx);
                    previews.done();
                }
            }
        }
    }
}
