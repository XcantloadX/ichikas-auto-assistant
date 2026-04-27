import QtQuick
import QtQuick.Controls

Window {
    id: root
    width: 960
    height: 600
    visible: scrcpyController.visible
    title: "Scrcpy 画面"
    color: "transparent"

    Image {
        id: frameImage
        anchors.fill: parent
        fillMode: Image.PreserveAspectFit
        cache: false
        source: "image://scrcpy/current?" + scrcpyController.frameToken

        function updateMetrics() {
            scrcpyController.updateDisplayMetrics(
                width,
                height,
                sourceSize.width,
                sourceSize.height,
                paintedWidth,
                paintedHeight
            )
        }

        onStatusChanged: updateMetrics()
        onPaintedWidthChanged: updateMetrics()
        onPaintedHeightChanged: updateMetrics()
    }

    Label {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 12
        color: "white"
        text: scrcpyController.statusText
    }

    MouseArea {
        anchors.fill: parent
        onPressed: scrcpyController.touchDown(mouse.x, mouse.y)
        onPositionChanged: if (pressed) scrcpyController.touchMove(mouse.x, mouse.y)
        onReleased: scrcpyController.touchUp(mouse.x, mouse.y)
        onCanceled: scrcpyController.touchUp(mouse.x, mouse.y)
    }
}
