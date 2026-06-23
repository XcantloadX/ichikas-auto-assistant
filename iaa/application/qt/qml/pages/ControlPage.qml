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
    readonly property var progressMessageKeys: ({
        "就绪": "status.ready",
        "已停止": "status.stopped",
        "开始执行": "progress.task_started",
        "执行完成": "progress.task_finished",
        "正在返回首页": "progress.returning_home",
        "扫描中": "progress.scanning",
        "阅读剧情": "progress.reading_story",
        "播放广告": "progress.playing_ad",
        "等待广告载入": "progress.waiting_ad_load",
        "等待广告结束": "progress.waiting_ad_end",
        "奖励已领取": "progress.reward_claimed",
        "等待结果": "progress.waiting_result",
        "正在前往交叉路口": "progress.going_scramble_crossing",
        "正在打开 CM 界面": "progress.opening_cm",
        "扫描列表": "progress.scanning_list",
        "前往任务奖励页面": "progress.opening_mission_rewards",
        "准备自动演出参数": "progress.preparing_auto_live",
        "返回首页准备进入演出": "progress.returning_home_before_live",
        "进入自动演出流程": "progress.entering_auto_live",
        "设置 AP 倍率": "progress.setting_ap_multiplier",
        "AP 不足，正在退出": "progress.not_enough_ap_exiting",
        "自动编队中": "progress.auto_team_setup",
        "结算中": "progress.settling_results",
        "进入单人演出": "progress.entering_solo_live",
        "准备开始演出": "progress.preparing_live",
        "演出中": "progress.live_in_progress",
        "开始单曲循环（游戏自动）": "progress.single_loop_game_auto",
        "单曲循环完成，返回首页": "progress.single_loop_complete",
        "开始单曲循环（脚本自动）": "progress.single_loop_script_auto",
        "开始列表循环": "progress.list_loop_start",
        "列表循环完成": "progress.list_loop_complete",
        "进入挑战演出": "progress.entering_challenge_live",
        "开始挑战演出": "progress.starting_challenge_live",
        "挑战演出完成，返回首页": "progress.challenge_live_complete"
    })

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
        var progressKey = root.progressMessageKeys[text]
        if (progressKey) {
            return App.Globals.t(progressKey)
        }
        if (text.indexOf("任务奖励 ") === 0) {
            return App.Globals.t("progress.mission_reward").replace(
                "{value}",
                text.replace("任务奖励 ", "")
            )
        }
        if (text.indexOf("选择角色：") === 0) {
            return App.Globals.t("progress.select_character").replace(
                "{character}",
                text.replace("选择角色：", "")
            )
        }
        if (text.indexOf("通过 ") === 0 && text.indexOf(" 进行引继") > 0) {
            return App.Globals.t("progress.transfer_account").replace(
                "{account}",
                text.replace("通过 ", "").replace(" 进行引继", "")
            )
        }
        if (text.indexOf("执行「") === 0 && text.indexOf("」时出错：") > 0) {
            var errorDelimiter = "」时出错："
            var taskEnd = text.indexOf(errorDelimiter)
            var taskName = text.substring(3, taskEnd)
            var taskError = text.substring(taskEnd + errorDelimiter.length)
            var taskErrorId = root.taskIdFromDisplayName(taskName)
            return App.Globals.t("progress.task_error")
                .replace("{task}", taskErrorId ? App.Globals.taskName(taskErrorId, taskName) : taskName)
                .replace("{error}", taskError === "未知错误" ? App.Globals.t("progress.unknown_error") : taskError)
        }
        if (text.indexOf("任务中断：") === 0) {
            var interruptedTask = text.replace("任务中断：", "")
            var interruptedTaskId = root.taskIdFromDisplayName(interruptedTask)
            return App.Globals.t("progress.task_interrupted").replace(
                "{task}",
                interruptedTaskId ? App.Globals.taskName(interruptedTaskId, interruptedTask) : interruptedTask
            )
        }
        if (text.indexOf("执行失败：") === 0) {
            var failedTask = text.replace("执行失败：", "")
            var failedTaskId = root.taskIdFromDisplayName(failedTask)
            return App.Globals.t("progress.task_failed").replace(
                "{task}",
                failedTaskId ? App.Globals.taskName(failedTaskId, failedTask) : failedTask
            )
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
                    text: root.displayStatusText(progressBridge.lastErrorText)
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
