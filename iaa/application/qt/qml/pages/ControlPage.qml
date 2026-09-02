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
            title: App.Globals.t("control.group.run")

            ColumnLayout {
                anchors.fill: parent
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    Button {
<<<<<<< HEAD
                        text: {
                            if (root.ctrl_isQueued)   return "排队中"
                            if (root.ctrl_isStarting) return "启动中"
                            if (root.ctrl_isStopping) return "停止中"
                            if (root.ctrl_running)    return "停止"
                            return "启动"
                        }
                        enabled: !root.ctrl_busy
                        highlighted: !root.ctrl_running
=======
                        text: runController.isStarting
                            ? App.Globals.t("control.starting")
                            : (runController.isStopping
                                ? App.Globals.t("control.stopping")
                                : (runController.running ? App.Globals.t("control.stop") : App.Globals.t("control.start")))
                        enabled: !runController.isStarting && !runController.isStopping
                        highlighted: !runController.running
>>>>>>> feat/en-server
                        onClicked: {
                            if (root.ctrl_running) root.runCtrl.stop()
                            else if (root.runCtrl) root.runCtrl.startRegular()
                        }
                    }
                    Button {
<<<<<<< HEAD
                        text: root.ctrl_exportBusy ? "导出中..." : "导出报告"
                        enabled: !root.ctrl_exportBusy
                        onClicked: { if (root.runCtrl) root.runCtrl.exportReport() }
                    }
                    Item { Layout.fillWidth: true }
                    Label { text: root.ctrl_taskName ? "当前任务：" + root.ctrl_taskName : "" }
=======
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
>>>>>>> feat/en-server
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
            Layout.minimumWidth: 0
            implicitWidth: 0
            title: App.Globals.t("control.group.tasks")

            ScrollView {
                id: taskScroll
                anchors.fill: parent
                implicitWidth: 0
                clip: true
                contentWidth: width
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                GridLayout {
                    id: taskGrid
                    width: taskScroll.width
                    columns: 3
                    rowSpacing: 8
                    columnSpacing: 8

                    Repeater {
                        model: root.tasks
                        delegate: Frame {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            Layout.preferredWidth: (
                                taskGrid.width - taskGrid.columnSpacing * (taskGrid.columns - 1)
                            ) / taskGrid.columns
                            Layout.preferredHeight: 76
                            padding: 10

                            RowLayout {
                                anchors.fill: parent
                                spacing: 10

                                Switch {
                                    visible: !!modelData.checkable
                                    checked: !!modelData.enabled
<<<<<<< HEAD
                                    enabled: !root.ctrl_busy
                                    text: modelData.name
                                    onToggled: { if (root.runCtrl) root.runCtrl.setRegularTaskEnabled(modelData.id, checked) }
=======
                                    enabled: !runController.running && !runController.isStarting && !runController.isStopping
                                    text: ""
                                    onToggled: runController.setRegularTaskEnabled(modelData.id, checked)
>>>>>>> feat/en-server
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: App.Globals.taskName(modelData.id, modelData.name)
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                    verticalAlignment: Text.AlignVCenter
                                }
                                Button {
<<<<<<< HEAD
                                    text: "运行"
                                    enabled: !root.ctrl_busy
=======
                                    Layout.preferredWidth: 78
                                    Layout.minimumWidth: 68
                                    text: App.Globals.t("control.run_task")
                                    enabled: !runController.running && !runController.isStarting && !runController.isStopping
>>>>>>> feat/en-server
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
