pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../components"
import "../components/form"

// 偏好页：QML 直写表单（kaa 风格）。编辑 shared 配置草稿。
PageContainer {
    id: root
    title: "偏好"

    titleRightContent: Rectangle {
        visible: root.dirty
        color: "#FFEBE9"
        border.color: "#DC3545"
        radius: 4
        implicitHeight: 32
        width: labelId.implicitWidth + 16

        Label {
            id: labelId
            text: "有未保存改动"
            color: "#DC3545"
            font.bold: true
            anchors.centerIn: parent
        }
    }

    headerActions: Button {
        text: "保存"
        highlighted: true
        enabled: root.dirty
        onClicked: root.prefsController.save()
    }

    required property var prefsController
    property bool dirty: false

    readonly property var config: root.prefsController.config

    readonly property var themeColorOptions: [
        {value: "", label: "跟随系统"},
        {value: "#0078d4", label: "蓝色（#0078D4）"},
        {value: "#e81123", label: "红色（#E81123）"},
        {value: "#107c10", label: "绿色（#107C10）"},
        {value: "#ff8c00", label: "橙色（#FF8C00）"},
        {value: "#5c2d91", label: "紫色（#5C2D91）"},
        {value: "#00b7c3", label: "青色（#00B7C3）"},
        {value: "#6b69d6", label: "靛蓝（#6B69D6）"},
        {value: "#4a5459", label: "石墨灰（#4A5459）"}
    ]

    FormBinder { id: formB; data: root.config; prefix: ""; errors: root.errors; onCommitted: root._commit("", key, value) }

    function _commit(prefix, key, value) {
        var path = prefix ? prefix + "." + key : key
        root.prefsController.setField(path, value)
    }

    function hasUnsavedChanges() { return root.prefsController.isDirty() }
    function discardChanges() { root.prefsController.discard() }
    function saveChanges() { return root.prefsController.save() }

    property var validationIssues: []

    readonly property var errors: (function() {
        var map = {}
        for (var i = 0; i < root.validationIssues.length; ++i) {
            var it = root.validationIssues[i]
            if (it && it.field) map[it.field] = {severity: it.severity, message: it.message}
        }
        return map
    })()

    function refreshValidation() {
        try {
            root.validationIssues = JSON.parse(root.prefsController.validateJson())
        } catch (e) {
            root.validationIssues = []
        }
    }

    Component.onCompleted: root.refreshValidation()

    Connections {
        target: root.prefsController
        function onConfigChanged() { root.refreshValidation() }
        function onDirtyChanged(value) { root.dirty = !!value; root.refreshValidation() }
    }

    ScrollView {
        id: scrollView
        anchors.fill: parent
        clip: true
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        ColumnLayout {
            width: scrollView.availableWidth
            spacing: 12

            // ── 数据收集 ────────────────────────────────────────────────
            FormGroupBox {
                title: "数据收集"
                FormCheckBox {
                    label: "自动发送匿名错误报告"
                    binder: formB
                    field: "telemetry.sentry"
                }
            }

            // ── 界面 ────────────────────────────────────────────────────
            FormGroupBox {
                title: "界面"
                FormComboBox {
                    label: "窗口背景样式"
                    binder: formB
                    field: "interface.window_style"
                    options: [
                        {value: "", label: "自动"},
                        {value: "mica", label: "Mica（仅 Win 11）"},
                        {value: "blur", label: "模糊背景"},
                        {value: "acrylic", label: "亚克力（Win 10 1803+）"},
                        {value: "solid", label: "纯色背景"}
                    ]
                }
                FormComboBox {
                    label: "色彩方案"
                    binder: formB
                    field: "interface.color_scheme"
                    options: [
                        {value: "auto", label: "跟随系统"},
                        {value: "light", label: "浅色"},
                        {value: "dark", label: "深色"}
                    ]
                }
                FormComboBox {
                    label: "启动时打开"
                    binder: formB
                    field: "interface.startup_page"
                    options: [
                        {value: "overview", label: "总览页面"},
                        {value: "last_opened", label: "上次打开的配置"}
                    ]
                }
                FormComboBox {
                    label: "主题色"
                    options: root.themeColorOptions
                    value: root.config.interface ? (root.config.interface.theme_color || "") : ""
                    onUserSelected: function(v) {
                        root.prefsController.setField("interface.theme_color", v ? v : null)
                    }
                }
            }

            // ── 通知 ────────────────────────────────────────────────────
            FormGroupBox {
                title: "通知"
                FormCheckBox {
                    label: "系统通知"
                    binder: formB
                    field: "notify.system"
                }
                FormCheckBox {
                    label: "推送通知"
                    binder: formB
                    field: "notify.push.enabled"
                }
                FormComboBox {
                    label: "推送类型"
                    options: [
                        {value: "custom", label: "自定义命令"},
                        {value: "discord", label: "Discord Webhook"}
                    ]
                    value: root.config.notify && root.config.notify.push ? root.config.notify.push.data.type : "custom"
                    visible: root.config.notify && root.config.notify.push.enabled
                    onUserSelected: function(v) {
                        // 切换类型时整体替换 data 实例，type 与数据始终保持一致
                        if (v === "discord") {
                            root.prefsController.setField("notify.push.data", {type: "discord", webhook_url: ""})
                        } else {
                            root.prefsController.setField("notify.push.data", {type: "custom", command: ""})
                        }
                    }
                }
                FormTextField {
                    label: "自定义命令"
                    placeholder: "任务完成后执行的命令"
                    value: (root.config.notify && root.config.notify.push && root.config.notify.push.data.type === "custom")
                        ? root.config.notify.push.data.command : ""
                    visible: root.config.notify && root.config.notify.push.enabled
                             && root.config.notify.push.data.type === "custom"
                    onUserEdited: function(v) { root.prefsController.setField("notify.push.data.command", v) }
                }
                FormTextField {
                    label: "Webhook URL"
                    placeholder: "https://discord.com/api/webhooks/..."
                    help: "<a href=\"https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks\">如何获取 Discord Webhook URL？</a>"
                    value: (root.config.notify && root.config.notify.push && root.config.notify.push.data.type === "discord")
                        ? root.config.notify.push.data.webhook_url : ""
                    visible: root.config.notify && root.config.notify.push.enabled
                             && root.config.notify.push.data.type === "discord"
                    onUserEdited: function(v) { root.prefsController.setField("notify.push.data.webhook_url", v) }
                }
            }

            // ── 快捷键 ──────────────────────────────────────────────────
            FormGroupBox {
                title: "快捷键"
                HotkeyField {
                    label: "启动脚本"
                    value: root.config.hotkeys ? (root.config.hotkeys.start || "") : ""
                    onUserCommitted: function(v) {
                        root.prefsController.setField("hotkeys.start", v ? v : null)
                    }
                }
                HotkeyField {
                    label: "停止脚本"
                    value: root.config.hotkeys ? (root.config.hotkeys.stop || "") : ""
                    onUserCommitted: function(v) {
                        root.prefsController.setField("hotkeys.stop", v ? v : null)
                    }
                }
            }
        }
    }
}
