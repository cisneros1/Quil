// {{full_name}} splash screen. Generated from palette.json by tools/build.py.
import QtQuick

Rectangle {
    id: root
    color: "{{bg}}"

    // Set by ksplashqml as Plasma starts up (1 to 6).
    property int stage

    Column {
        anchors.centerIn: parent
        spacing: 28
        opacity: root.stage >= 1 ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 600 } }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "{{name}}"
            color: "{{fg}}"
            font.pixelSize: 64
            font.weight: Font.Light
            font.letterSpacing: 8
        }

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 220
            height: 3
            radius: 1.5
            color: "{{bg_alt}}"

            Rectangle {
                height: parent.height
                radius: parent.radius
                color: "{{accent}}"
                width: parent.width * Math.min(root.stage, 6) / 6
                Behavior on width { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }
            }
        }
    }
}
