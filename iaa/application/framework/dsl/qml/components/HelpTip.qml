import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    implicitWidth: 18
    implicitHeight: 18

    property string richText: ""
    property int maxPopupWidth: 360
    property int openDelay: 220
    property int closeDelay: 140
    readonly property bool hovering: iconMouse.containsMouse || popupMouse.containsMouse

    function updatePopupPosition() {
        if (!tipPopup.parent) {
            return;
        }
        var p = root.mapToItem(tipPopup.parent, 0, root.height + 6);
        tipPopup.x = p.x;
        tipPopup.y = p.y;
    }

    onHoveringChanged: {
        if (!richText || richText.length === 0) {
            openTimer.stop();
            closeTimer.stop();
            return;
        }
        if (hovering) {
            closeTimer.stop();
            openTimer.restart();
        } else {
            openTimer.stop();
            closeTimer.restart();
        }
    }

    Timer {
        id: openTimer
        interval: root.openDelay
        repeat: false
        onTriggered: {
            root.updatePopupPosition();
            tipPopup.open();
        }
    }

    Timer {
        id: closeTimer
        interval: root.closeDelay
        repeat: false
        onTriggered: tipPopup.close()
    }

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: iconMouse.containsMouse ? "#2D6CDF" : "#9CA3AF"

        Text {
            anchors.centerIn: parent
            text: "?"
            color: "white"
            font.pixelSize: 12
            font.bold: true
        }
    }

    MouseArea {
        id: iconMouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }

    Popup {
        id: tipPopup
        parent: Overlay.overlay
        width: Math.min(root.maxPopupWidth, contentLabel.implicitWidth + leftPadding + rightPadding)
        padding: 10
        modal: false
        focus: false
        closePolicy: Popup.NoAutoClose

        background: Rectangle {
            color: "#1F2937"
            radius: 6
            border.color: "#111827"
            border.width: 1
            opacity: 0.96
        }

        contentItem: Label {
            id: contentLabel
            width: Math.min(root.maxPopupWidth - tipPopup.leftPadding - tipPopup.rightPadding, implicitWidth)
            wrapMode: Text.Wrap
            textFormat: Text.RichText
            text: root.richText
            color: "#F9FAFB"
            lineHeight: 1.2
        }

        MouseArea {
            id: popupMouse
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.NoButton
        }

        onOpened: root.updatePopupPosition()
        onWidthChanged: root.updatePopupPosition()
    }
}
