import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".." as App

Item {
    id: root
    required property var session
    property bool scriptRunning: false

    readonly property bool hasSession: session !== null && session !== undefined

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Button {
                id: powerBtn
                enabled: root.hasSession
                leftPadding: 12
                rightPadding: 12
                topPadding: 6
                bottomPadding: 6
                contentItem: Row {
                    spacing: 6
                    anchors.centerIn: parent

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        font.family: "FluentSystemIcons-Regular"
                        font.pixelSize: 16
                        text: "\uF60E"   // FluentSystemIcons power_20
                        color: powerBtn.enabled ? App.IaaTheme.fg : palette.placeholderText
                    }

                    Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.hasSession && session.deviceRunning ? App.Globals.t("control.stop") : App.Globals.t("control.start")
                        // font.pixelSize: 14
                        color: powerBtn.enabled ? App.IaaTheme.fg : palette.placeholderText
                    }
                }
                onClicked: {
                    if (!root.hasSession) {
                        return
                    }
                    if (session.deviceRunning) {
                        App.Modal.message({
                            title: App.Globals.t("page.device.stop_game_title"),
                            content: root.scriptRunning
                                ? App.Globals.t("page.device.stop_game_script_running")
                                : App.Globals.t("page.device.stop_game_confirm"),
                            buttons: [
                                { text: App.Globals.t("common.cancel"), value: "cancel" },
                                { text: App.Globals.t("control.stop"), value: "ok", highlighted: true }
                            ],
                            width: 360
                        }, function(result) {
                            if (result === "ok") {
                                session.stop_device()
                            }
                        })
                    } else {
                        session.start_device()
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#000000"
            radius: 6
            clip: true

            Image {
                id: frameImage
                anchors.fill: parent
                fillMode: Image.PreserveAspectFit
                cache: false
                visible: root.hasSession && session.deviceRunning
                source: root.hasSession && session.deviceRunning
                    ? ("image://scrcpy/" + session.imageKey + "?" + session.frameToken)
                    : ""

                function updateMetrics() {
                    if (!root.hasSession) {
                        return
                    }
                    session.updateDisplayMetrics(
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

            MouseArea {
                anchors.fill: parent
                enabled: root.hasSession && session.deviceRunning
                onPressed: function(mouse) {
                    session.touchDown(mouse.x, mouse.y)
                }
                onPositionChanged: function(mouse) {
                    if (pressed) {
                        session.touchMove(mouse.x, mouse.y)
                    }
                }
                onReleased: function(mouse) {
                    session.touchUp(mouse.x, mouse.y)
                }
                onCanceled: function(mouse) {
                    session.touchUp(mouse.x, mouse.y)
                }
            }
        }
    }

    onVisibleChanged: {
        if (root.hasSession) {
            session.setViewVisible(visible)
        }
    }

    Component.onCompleted: {
        if (root.hasSession && visible) {
            session.setViewVisible(true)
        }
    }
}