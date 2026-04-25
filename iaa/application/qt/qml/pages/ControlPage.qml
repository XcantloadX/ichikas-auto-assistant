import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

PageContainer {
    id: root
    title: "控制"
    property var tasks: []
    property var autoLiveDialog
    signal showNotice(string kind, string text)

    function reloadTasks() {
        tasks = JSON.parse(runController.tasksStateJson())
    }

    Component.onCompleted: reloadTasks()

    Connections {
        target: runController
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
                        runController.runTask("main_story")
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
                        text: runController.isStarting ? "启动中" : (runController.isStopping ? "停止中" : (runController.running ? "停止" : "启动"))
                        enabled: !runController.isStarting && !runController.isStopping
                        highlighted: !runController.running
                        onClicked: {
                            if (runController.running) {
                                runController.stop()
                            } else {
                                runController.startRegular()
                            }
                        }
                    }
                    Button {
                        text: runController.exportBusy ? "导出中..." : "导出报告"
                        enabled: !runController.exportBusy
                        onClicked: runController.exportReport()
                    }
                    Item { Layout.fillWidth: true }
                    Label { text: runController.currentTaskName ? ("当前任务：" + runController.currentTaskName) : "" }
                }

                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    text: progressBridge.statusText
                }
                ProgressBar {
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    value: progressBridge.progressPercent
                }
                Label {
                    Layout.fillWidth: true
                    visible: !!progressBridge.lastErrorText
                    color: "#b91c1c"
                    wrapMode: Text.Wrap
                    text: progressBridge.lastErrorText
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
                                CheckBox {
                                    visible: !!modelData.checkable
                                    checked: !!modelData.enabled
                                    enabled: !runController.running && !runController.isStarting && !runController.isStopping
                                    text: modelData.name
                                    onToggled: runController.setRegularTaskEnabled(modelData.id, checked)
                                }
                                Label {
                                    visible: !modelData.checkable
                                    text: modelData.name
                                }
                                Item { Layout.fillWidth: true }
                                Button {
                                    text: "运行"
                                    enabled: !runController.running && !runController.isStarting && !runController.isStopping
                                    onClicked: {
                                        if (modelData.id === "auto_live") {
                                            root.autoLiveDialog.open()
                                        } else if (modelData.id === "main_story") {
                                            mainStoryDialog.open()
                                        } else {
                                            runController.runTask(modelData.id)
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
