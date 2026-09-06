pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import ".." as App
import "../components"
import "../components/form"

// 偏好页：QML 直写表单（kaa 风格）。编辑 shared 配置草稿。
PageContainer {
    id: root
    title: App.Globals.t("nav.preferences")

    titleRightContent: Rectangle {
        visible: root.dirty
        color: "#FFEBE9"
        border.color: "#DC3545"
        radius: 4
        implicitHeight: 32
        width: labelId.implicitWidth + 16

        Label {
            id: labelId
            text: App.Globals.t("common.unsaved_changes")
            color: "#DC3545"
            font.bold: true
            anchors.centerIn: parent
        }
    }

    headerActions: Button {
        text: App.Globals.t("common.save")
        highlighted: true
        enabled: root.dirty
        onClicked: root.prefsController.save()
    }

    required property var prefsController
    property bool dirty: false

    readonly property var config: root.prefsController.config

    readonly property var themeColorOptions: [
        {value: "", label: App.Globals.t("preferences.option.follow_system")},
        {value: "#0078d4", label: App.Globals.t("preferences.option.theme.blue")},
        {value: "#e81123", label: App.Globals.t("preferences.option.theme.red")},
        {value: "#107c10", label: App.Globals.t("preferences.option.theme.green")},
        {value: "#ff8c00", label: App.Globals.t("preferences.option.theme.orange")},
        {value: "#5c2d91", label: App.Globals.t("preferences.option.theme.purple")},
        {value: "#00b7c3", label: App.Globals.t("preferences.option.theme.cyan")},
        {value: "#6b69d6", label: App.Globals.t("preferences.option.theme.indigo")},
        {value: "#4a5459", label: App.Globals.t("preferences.option.theme.graphite")}
    ]

    FormBinder { id: formB; data: root.config; prefix: ""; errors: root.errors; onCommitted: function(key, value) { root._commit("", key, value) } }

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
                title: App.Globals.t("preferences.group.telemetry")
                FormCheckBox {
                    label: App.Globals.t("preferences.field.telemetry_sentry")
                    binder: formB
                    field: "telemetry.sentry"
                }
                FormCheckBox {
                    label: App.Globals.t("preferences.field.telemetry_upload_screenshot")
                    binder: formB
                    field: "telemetry.upload_screenshot"
                }
                FormCheckBox {
                    label: App.Globals.t("preferences.field.telemetry_statics")
                    binder: formB
                    field: "telemetry.statics"
                }
            }

            // ── 界面 ────────────────────────────────────────────────────
            FormGroupBox {
                title: App.Globals.t("preferences.group.interface")
                FormComboBox {
                    label: App.Globals.t("preferences.field.language")
                    binder: formB
                    field: "interface.language"
                    options: [
                        {value: "auto", label: App.Globals.t("preferences.option.auto")},
                        {value: "zh_CN", label: App.Globals.t("preferences.language.zh_CN")},
                        {value: "en_US", label: App.Globals.t("preferences.language.en_US")}
                    ]
                }
                FormComboBox {
                    label: App.Globals.t("preferences.field.window_style")
                    binder: formB
                    field: "interface.window_style"
                    options: [
                        {value: "", label: App.Globals.t("preferences.option.auto")},
                        {value: "mica", label: App.Globals.t("preferences.option.window_style.mica")},
                        {value: "blur", label: App.Globals.t("preferences.option.window_style.blur")},
                        {value: "acrylic", label: App.Globals.t("preferences.option.window_style.acrylic")},
                        {value: "solid", label: App.Globals.t("preferences.option.window_style.solid")}
                    ]
                }
                FormComboBox {
                    label: App.Globals.t("preferences.field.color_scheme")
                    binder: formB
                    field: "interface.color_scheme"
                    options: [
                        {value: "auto", label: App.Globals.t("preferences.option.follow_system")},
                        {value: "light", label: App.Globals.t("preferences.option.color_scheme.light")},
                        {value: "dark", label: App.Globals.t("preferences.option.color_scheme.dark")}
                    ]
                }
                FormComboBox {
                    label: App.Globals.t("preferences.field.startup_page")
                    binder: formB
                    field: "interface.startup_page"
                    options: [
                        {value: "overview", label: App.Globals.t("preferences.option.startup_page.overview")},
                        {value: "last_opened", label: App.Globals.t("preferences.option.startup_page.last_opened")}
                    ]
                }
                FormComboBox {
                    label: App.Globals.t("preferences.field.theme_color")
                    options: root.themeColorOptions
                    value: root.config.interface ? (root.config.interface.theme_color || "") : ""
                    onUserSelected: function(v) {
                        root.prefsController.setField("interface.theme_color", v ? v : null)
                    }
                }
            }

            // ── 通知 ────────────────────────────────────────────────────
            FormGroupBox {
                title: App.Globals.t("preferences.group.notify")
                FormCheckBox {
                    label: App.Globals.t("preferences.field.notify_system")
                    binder: formB
                    field: "notify.system"
                }
                FormCheckBox {
                    label: App.Globals.t("preferences.field.notify_push")
                    binder: formB
                    field: "notify.push.enabled"
                }
                FormComboBox {
                    label: App.Globals.t("preferences.field.notify_push_type")
                    options: [
                        {value: "custom", label: App.Globals.t("preferences.option.notify_push.custom")},
                        {value: "discord", label: App.Globals.t("preferences.option.notify_push.discord")}
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
                    label: App.Globals.t("preferences.field.notify_custom_command")
                    placeholder: App.Globals.t("preferences.placeholder.notify_custom_command")
                    value: (root.config.notify && root.config.notify.push && root.config.notify.push.data.type === "custom")
                        ? root.config.notify.push.data.command : ""
                    visible: root.config.notify && root.config.notify.push.enabled
                             && root.config.notify.push.data.type === "custom"
                    onUserEdited: function(v) { root.prefsController.setField("notify.push.data.command", v) }
                }
                FormTextField {
                    label: "Webhook URL"
                    placeholder: "https://discord.com/api/webhooks/..."
                    help: "<a href=\"https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks\">" + App.Globals.t("preferences.help.discord_webhook") + "</a>"
                    value: (root.config.notify && root.config.notify.push && root.config.notify.push.data.type === "discord")
                        ? root.config.notify.push.data.webhook_url : ""
                    visible: root.config.notify && root.config.notify.push.enabled
                             && root.config.notify.push.data.type === "discord"
                    onUserEdited: function(v) { root.prefsController.setField("notify.push.data.webhook_url", v) }
                }
            }

            // ── 快捷键 ──────────────────────────────────────────────────
            FormGroupBox {
                title: App.Globals.t("preferences.group.hotkeys")
                HotkeyField {
                    label: App.Globals.t("preferences.field.hotkey_start")
                    value: root.config.hotkeys ? (root.config.hotkeys.start || "") : ""
                    onUserCommitted: function(v) {
                        root.prefsController.setField("hotkeys.start", v ? v : null)
                    }
                }
                HotkeyField {
                    label: App.Globals.t("preferences.field.hotkey_stop")
                    value: root.config.hotkeys ? (root.config.hotkeys.stop || "") : ""
                    onUserCommitted: function(v) {
                        root.prefsController.setField("hotkeys.stop", v ? v : null)
                    }
                }
            }
        }
    }
}
