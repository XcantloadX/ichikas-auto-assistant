import QtQuick
import QtQuick.Controls
import ".." as App

Window {
    id: root
    width: 960
    height: 600
    visible: scrcpyController.visible
    title: App.Globals.t("scrcpy.title")
    color: "transparent"

    function displayStatusText(text) {
        var value = String(text || "")
        if (value === "等待画面...") {
            return App.Globals.t("scrcpy.waiting_frame")
        }
        if (value.indexOf("等待画面... ") === 0) {
            return App.Globals.t("scrcpy.waiting_frame_error").replace(
                "{error}",
                value.replace("等待画面... ", "")
            )
        }
        return value
    }

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
        text: root.displayStatusText(scrcpyController.statusText)
    }

    MouseArea {
        anchors.fill: parent
        onPressed: scrcpyController.touchDown(mouse.x, mouse.y)
        onPositionChanged: if (pressed) scrcpyController.touchMove(mouse.x, mouse.y)
        onReleased: scrcpyController.touchUp(mouse.x, mouse.y)
        onCanceled: scrcpyController.touchUp(mouse.x, mouse.y)
    }
}
