import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".." as App
import "../components"

PageContainer {
    id: root
    title: App.Globals.t("nav.control")
    property var tasks: []
    property var autoLiveDialog

    function reloadTasks() {
        tasks = JSON.parse(runController.tasksStateJson())
    }

    function taskIdFromDisplayName(name) {
        for (var i = 0; i < tasks.length; i++) {
            if (tasks[i].name === name) {
                return tasks[i].id
            }
        }
        return ""
    }

    function displayStatusPart(text) {
        var taskId = root.taskIdFromDisplayName(text)
        if (taskId) {
            return App.Globals.taskName(taskId, text)
        }
        if (text === "就绪") {
            return App.Globals.t("status.ready")
        }
        if (text === "已停止") {
            return App.Globals.t("status.stopped")
        }
        if (text === "开始执行") {
            return App.Globals.t("progress.task_started")
        }
        if (text === "执行完成") {
            return App.Globals.t("progress.task_finished")
        }
        return text
    }

    function displayStatusText(text) {
        var parts = String(text || "").split(" > ")
        for (var i = 0; i < parts.length; i++) {
            parts[i] = root.displayStatusPart(parts[i])
        }
        return parts.join(" > ")
    }

    Component.onCompleted: reloadTasks()

    Connections {
        target: runController
        function onTasksChanged() { root.reloadTasks() }
    }

    Dialog {
        id: mainStoryDialog
        title: App.Globals.t("control.main_story_confirm.title")
        modal: true
        standardButtons: Dialog.NoButton
        width: 420
        anchors.centerIn: Overlay.overlay
        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: App.Globals.t("control.main_story_confirm.content")
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button { text: App.Globals.t("common.cancel"); onClicked: mainStoryDialog.close() }
                Button {
                    text: App.Globals.t("common.start")
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
            title: App.Globals.t("control.group.run")

            ColumnLayout {
                anchors.fill: parent
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        text: runController.isStarting
                            ? App.Globals.t("control.starting")
                            : (runController.isStopping
                                ? App.Globals.t("control.stopping")
                                : (runController.running ? App.Globals.t("control.stop") : App.Globals.t("control.start")))
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
                        text: runController.exportBusy ? App.Globals.t("control.exporting_report") : App.Globals.t("control.export_report")
                        enabled: !runController.exportBusy
                        onClicked: runController.exportReport()
                    }
                    Item { Layout.fillWidth: true }
                    Label {
                        text: runController.currentTaskId
                            ? App.Globals.t("control.current_task").replace(
                                "{task}",
                                App.Globals.taskName(runController.currentTaskId, runController.currentTaskName)
                            )
                            : ""
                    }
                }

                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    text: root.displayStatusText(progressBridge.statusText)
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
            title: App.Globals.t("control.group.tasks")

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
                                    enabled: !runController.running && !runController.isStarting && !runController.isStopping
                                    text: App.Globals.taskName(modelData.id, modelData.name)
                                    onToggled: runController.setRegularTaskEnabled(modelData.id, checked)
                                }
                                Label {
                                    visible: !modelData.checkable
                                    text: App.Globals.taskName(modelData.id, modelData.name)
                                }
                                Item { Layout.fillWidth: true }
                                Button {
                                    text: App.Globals.t("control.run_task")
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
