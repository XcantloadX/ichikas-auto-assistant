import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

PageContainer {
    id: root
    title: "控制"
    property var tasks: []
    property var autoLiveDialog
    required property var runCtrl
    required property var progBridge

    readonly property bool ctrl_running:    runCtrl ? runCtrl.running    : false
    readonly property bool ctrl_isStarting: runCtrl ? runCtrl.isStarting : false
    readonly property bool ctrl_isStopping: runCtrl ? runCtrl.isStopping : false
    readonly property bool ctrl_isQueued:   runCtrl ? runCtrl.isQueued   : false
    readonly property bool ctrl_exportBusy: runCtrl ? runCtrl.exportBusy : false
    readonly property string ctrl_taskName: runCtrl ? runCtrl.currentTaskName : ""
    readonly property bool ctrl_busy: ctrl_isStarting || ctrl_isStopping || ctrl_isQueued

    function reloadTasks() {
        tasks = root.runCtrl ? JSON.parse(root.runCtrl.tasksStateJson()) : []
    }

    Component.onCompleted: reloadTasks()

    Connections {
        target: root.runCtrl
        function onTasksChanged() { root.reloadTasks() }
    }

    Dialog {
        id: mainStoryDialog
        title: "确认开始"
        modal: true
        standardButtons: Dialog.NoButton
        width: 420
        anchors.centerIn: Overlay.overlay
        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: "即将开始刷往期剧情，脚本会无限执行，需要手动停止。是否继续？"
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button { text: "取消"; onClicked: mainStoryDialog.close() }
                Button {
                    text: "开始"
                    highlighted: true
                    onClicked: {
                        mainStoryDialog.close()
                        if (root.runCtrl) root.runCtrl.runTask("main_story")
                    }
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        GroupBox {
            Layout.fillWidth: true
            title: "启停"

            ColumnLayout {
                anchors.fill: parent
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        text: {
                            if (root.ctrl_isQueued)   return "排队中"
                            if (root.ctrl_isStarting) return "启动中"
                            if (root.ctrl_isStopping) return "停止中"
                            if (root.ctrl_running)    return "停止"
                            return "启动"
                        }
                        enabled: !root.ctrl_busy
                        highlighted: !root.ctrl_running
                        onClicked: {
                            if (root.ctrl_running) root.runCtrl.stop()
                            else if (root.runCtrl) root.runCtrl.startRegular()
                        }
                    }
                    Button {
                        text: root.ctrl_exportBusy ? "导出中..." : "导出报告"
                        enabled: !root.ctrl_exportBusy
                        onClicked: { if (root.runCtrl) root.runCtrl.exportReport() }
                    }
                    Item { Layout.fillWidth: true }
                    Label { text: root.ctrl_taskName ? "当前任务：" + root.ctrl_taskName : "" }
                }

                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    text: root.progBridge ? root.progBridge.statusText : ""
                }
                ProgressBar {
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    value: root.progBridge ? root.progBridge.progressPercent : 0
                }
                Label {
                    Layout.fillWidth: true
                    visible: !!(root.progBridge && root.progBridge.lastErrorText)
                    color: "#b91c1c"
                    wrapMode: Text.Wrap
                    text: root.progBridge ? root.progBridge.lastErrorText : ""
                }
            }
        }

        GroupBox {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "任务"

            ScrollView {
                anchors.fill: parent
                clip: true

                GridLayout {
                    width: parent.width
                    columns: 3
                    rowSpacing: 8
                    columnSpacing: 8

                    Repeater {
                        model: root.tasks
                        delegate: Frame {
                            Layout.fillWidth: true
                            padding: 10
                            RowLayout {
                                anchors.fill: parent
                                Switch {
                                    visible: !!modelData.checkable
                                    checked: !!modelData.enabled
                                    enabled: !root.ctrl_busy
                                    text: modelData.name
                                    onToggled: { if (root.runCtrl) root.runCtrl.setRegularTaskEnabled(modelData.id, checked) }
                                }
                                Label {
                                    visible: !modelData.checkable
                                    text: modelData.name
                                }
                                Item { Layout.fillWidth: true }
                                Button {
                                    text: "运行"
                                    enabled: !root.ctrl_busy
                                    onClicked: {
                                        if (modelData.id === "auto_live") {
                                            root.autoLiveDialog.open()
                                        } else if (modelData.id === "main_story") {
                                            mainStoryDialog.open()
                                        } else if (root.runCtrl) {
                                            root.runCtrl.runTask(modelData.id)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
