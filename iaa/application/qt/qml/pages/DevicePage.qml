import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import ".." as App
import IaaApp 1.0

PageContainer {
    id: root
    title: App.Globals.t("nav.device")
    property int tabIndex: 0
    property var formController: null
    property var runCtrl: null
    property string controlImpl: ""

    readonly property bool scriptRunning: runCtrl ? runCtrl.running : false

    readonly property var deviceSession: TabManager.deviceSessionAt(tabIndex)
    readonly property bool scrcpyAvailable: controlImpl === "scrcpy"

    function syncControlImpl() {
        controlImpl = TabManager.deviceControlImplAt(tabIndex)
    }

    Component.onCompleted: syncControlImpl()

    Connections {
        target: root.formController
        function onConfigChanged() {
            root.syncControlImpl()
        }
    }

    DeviceView {
        anchors.fill: parent
        session: root.deviceSession
        scriptRunning: root.scriptRunning
    }

    Rectangle {
        anchors.fill: parent
        visible: !root.scrcpyAvailable
        color: App.IaaTheme.isDark ? Qt.rgba(0, 0, 0, 0.55) : Qt.rgba(1, 1, 1, 0.72)
        z: 1

        Label {
            anchors.centerIn: parent
            width: Math.min(parent.width - 48, 360)
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            font.pixelSize: 15
            color: App.IaaTheme.fg
            text: App.Globals.t("page.device.scrcpy_only_hint")
        }
    }
}
