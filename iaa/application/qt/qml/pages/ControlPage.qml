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
                                    enabled: !runController.running && !runController.isStarting && !runController.isStopping
                                    text: ""
                                    onToggled: runController.setRegularTaskEnabled(modelData.id, checked)
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
                                    Layout.preferredWidth: 78
                                    Layout.minimumWidth: 68
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
