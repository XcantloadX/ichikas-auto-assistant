pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import ".." as App
import "../components"
import "../components/form"
import ".." as App

// 设置页：QML 直写表单（kaa 风格）。表单定义直接声明在这里，
// 通过 FormBinder 与 SettingsController.config（base+dirty 草稿视图）双向绑定，
// setField 写入草稿，save 归一化 + 校验 + 写盘。
PageContainer {
    id: root
    title: App.Globals.t("nav.config")

    titleRightContent: RowLayout {
        spacing: 8
        Rectangle {
            visible: root.scriptRunning
            color: "#FEF3C7"
            border.color: "#F59E0B"
            radius: 4
            implicitHeight: 32
            width: runningLabel.implicitWidth + 16

            Label {
                id: runningLabel
                text: App.Globals.t("page.settings.script_running")
                color: "#B45309"
                font.bold: true
                anchors.centerIn: parent
            }
        }
        Rectangle {
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
    }

    headerActions: Button {
        text: App.Globals.t("common.save")
        highlighted: true
        enabled: root.dirty && !root.scriptRunning
        onClicked: root.formController.save()
    }

    required property var formController
    property var runCtrl: null
    readonly property bool scriptRunning: runCtrl ? (runCtrl.running || runCtrl.isStarting || runCtrl.isStopping) : false

    property bool dirty: false
    property var validationIssues: []

    // ── 选项数据（从 controller 加载，Python 侧保持单一数据源）──
    property var lifecycleOptions: []
    property var connectionOptions: []
    property var serverOptions: []
    property var linkOptions: []
    property var controlImplOptions: []
    property var resolutionOptions: []
    property var challengeCharacters: []
    property var challengeAwards: []
    property var eventShopItems: []

    // ── 模拟器实例 ──
    property var mumuInstances: []
    property bool mumuEnumerationLoading: false
    property var avdInstances: []
    property bool avdEnumerationLoading: false

    readonly property var songNameOptions: [
        {label: App.Globals.t("settings.option.live.song.keep"), value: "保持不变"},
        {label: "メルト", value: "メルト"},
        {label: "独りんぼエンヴィー", value: "独りんぼエンヴィー"}
    ]
    readonly property var apMultiplierOptions: [
        {label: App.Globals.t("settings.option.live.ap.keep"), value: "保持现状"},
        {label: App.Globals.t("settings.option.live.ap.maximum"), value: "maximum"},
        {label: "0", value: "0"}, {label: "1", value: "1"}, {label: "2", value: "2"},
        {label: "3", value: "3"}, {label: "4", value: "4"}, {label: "5", value: "5"},
        {label: "6", value: "6"}, {label: "7", value: "7"}, {label: "8", value: "8"},
        {label: "9", value: "9"}, {label: "10", value: "10"}
    ]

    // ── 草稿视图 ──
    readonly property var config: root.formController.config

    // ── 派生状态 ──
    readonly property string lcType: {
        var lc = (root.config && root.config.device) ? root.config.device.lifecycle : null
        return lc ? String(lc.type || "none") : "none"
    }
    readonly property string controlImpl: {
        var d = root.config ? root.config.device : null
        return d ? String(d.control_impl || "adb") : "adb"
    }
    readonly property string connType: {
        var conn = (root.config && root.config.device) ? root.config.device.connection : null
        if (conn && conn.type === "tcp") return "tcp"
        return "usb"
    }
    readonly property bool isMumu: root.lcType === "mumu" || root.lcType === "mumu_v5"
    readonly property bool hasLifecycle: root.isMumu || root.lcType === "custom" || root.lcType === "playcover" || root.lcType === "avd"
    readonly property bool showConnectionSection: !root.isMumu && root.lcType !== "playcover" && root.lcType !== "avd"
    readonly property bool lcCheckAndStart: {
        var lc = (root.config && root.config.device) ? root.config.device.lifecycle : null
        return lc ? !!lc.check_and_start : false
    }

    readonly property var controlImplOptionsForLc: {
        var isMumu = root.isMumu
        var isAvd = root.lcType === "avd"
        return root.controlImplOptions.filter(function(o) {
            if (o.value === "nemu_ipc" && !isMumu) return false
            if (o.value === "qemu_grpc" && !isAvd) return false
            return true
        })
    }
    readonly property var resolutionOptionsForImpl: {
        if (root.controlImpl === "qemu_grpc") {
            return [{value: "keep", label: App.Globals.t("settings.option.resolution.keep")}]
        }
        return root.resolutionOptions
    }

    // ── 校验问题映射：完整 dot path → {severity, message} ──
    readonly property var errors: (function() {
        var map = {}
        for (var i = 0; i < root.validationIssues.length; ++i) {
            var it = root.validationIssues[i]
            if (it && it.field) map[it.field] = {severity: it.severity, message: it.message}
        }
        return map
    })()

    // ── FieldRegistrar 宿主接口 ──
    property var _fieldLabels: ({})
    function registerField(path, label) { root._fieldLabels[path] = label }
    function unregisterField(path) { delete root._fieldLabels[path] }

    function _commit(prefix, key, value) {
        var path = prefix ? prefix + "." + key : key
        if (Array.isArray(value)) root.formController.setListField(path, value)
        else root.formController.setField(path, value)
    }

    function refreshValidation() {
        try {
            root.validationIssues = JSON.parse(root.formController.validateJson())
        } catch (e) {
            root.validationIssues = []
        }
    }

    function hasUnsavedChanges() { return root.formController.isDirty() }
    function discardChanges() { root.formController.discard() }
    function saveChanges() { root.formController.save() }

    // ── 设备类型 / 连接方式切换（整体替换 discriminated union 对象）──
    function setLifecycleType(type) {
        var device = root.config.device || {}
        var lc = device.lifecycle || {}
        var conn = device.connection || {}
        var newLc
        var newConn = null

        if (type === "mumu" || type === "mumu_v5") {
            newLc = { type: type }
            if (lc && (lc.type === "mumu" || lc.type === "mumu_v5")) {
                newLc.instance_id = lc.instance_id
                newLc.check_and_start = !!lc.check_and_start
            } else {
                newLc.check_and_start = false
            }
            newConn = { type: "auto" }
        } else if (type === "avd") {
            newLc = { type: "avd" }
            if (lc && lc.type === "avd") {
                newLc.sdk_path = lc.sdk_path || ""
                newLc.avd_name = lc.avd_name || ""
                newLc.extra_args = lc.extra_args || ""
                newLc.check_and_start = !!lc.check_and_start
            } else {
                newLc.sdk_path = ""
                newLc.avd_name = ""
                newLc.extra_args = ""
                newLc.check_and_start = false
            }
            newConn = { type: "auto" }
        } else if (type === "custom") {
            newLc = { type: "custom" }
            if (lc && lc.type === "custom") {
                newLc.start_command = lc.start_command || ""
                newLc.wait_start_command = !!lc.wait_start_command
                newLc.stop_command = lc.stop_command || ""
                newLc.running_command = lc.running_command || ""
                newLc.check_and_start = !!lc.check_and_start
            } else {
                newLc.start_command = ""
                newLc.wait_start_command = false
                newLc.stop_command = ""
                newLc.running_command = ""
                newLc.check_and_start = false
            }
            newConn = {
                type: "tcp",
                ip: (conn && conn.ip) || "127.0.0.1",
                port: (conn && conn.port !== undefined && conn.port !== null) ? conn.port : 5555,
                run_adb_connect: conn ? !!conn.run_adb_connect : true,
                device_serial: (conn && conn.device_serial) || ""
            }
        } else if (type === "playcover") {
            newLc = { type: "playcover", check_and_start: lc ? !!lc.check_and_start : false }
            // PlayCover 不展示连接设置，保持原 connection 不变
        } else { // none
            newLc = { type: "none" }
            newConn = { type: "usb", device_serial: (conn && conn.device_serial) || "" }
        }

        // control_impl 兼容性：切换后若当前控制方式不可用，回退到 adb
        var impl = root.controlImpl
        if (type === "mumu" || type === "mumu_v5") {
            // 全部可用
        } else if (type === "avd") {
            if (impl === "nemu_ipc") impl = "adb"
        } else {
            if (impl === "nemu_ipc" || impl === "qemu_grpc") impl = "adb"
        }

        root.formController.setField("device.lifecycle", newLc)
        if (newConn) root.formController.setField("device.connection", newConn)
        if (impl !== root.controlImpl) root.formController.setField("device.control_impl", impl)
    }

    function setConnectionType(type) {
        var conn = (root.config && root.config.device) ? root.config.device.connection || {} : {}
        if (type === "usb") {
            root.formController.setField("device.connection", {
                type: "usb",
                device_serial: conn.device_serial || ""
            })
        } else {
            root.formController.setField("device.connection", {
                type: "tcp",
                ip: conn.ip || "127.0.0.1",
                port: (conn.port !== undefined && conn.port !== null) ? conn.port : 5555,
                run_adb_connect: conn.run_adb_connect !== undefined ? !!conn.run_adb_connect : true,
                device_serial: conn.device_serial || ""
            })
        }
    }

    // ── 实例枚举 ──
    function refreshMumuInstances() {
        root.mumuEnumerationLoading = true
        root.formController.listEmulatorInstancesAsync(root.lcType)
    }
    function refreshAvdInstances() {
        root.avdEnumerationLoading = true
        root.formController.listEmulatorInstancesAsync("avd")
    }
    function handleInstancesReady(emulatorType, json) {
        if (emulatorType === "mumu" || emulatorType === "mumu_v5") {
            if (emulatorType !== root.lcType) return
            root.mumuInstances = JSON.parse(json)
            root.mumuEnumerationLoading = false
        } else if (emulatorType === "avd") {
            root.avdInstances = JSON.parse(json)
            root.avdEnumerationLoading = false
        }
    }

    // ── 表单绑定器 ──
    FormBinder { id: formB; data: root.config; prefix: ""; errors: root.errors; onCommitted: function(key, value) { root._commit("", key, value) } }
    FormBinder { id: lcB; data: root.config.device ? root.config.device.lifecycle : null; prefix: "device.lifecycle"; errors: root.errors; onCommitted: function(key, value) { root._commit("device.lifecycle", key, value) } }
    FormBinder { id: connB; data: root.config.device ? root.config.device.connection : null; prefix: "device.connection"; errors: root.errors; onCommitted: function(key, value) { root._commit("device.connection", key, value) } }

    // 选项文本由 Python 侧按当前语言解析，语言变化后需重新拉取
    function reloadOptions() {
        root.lifecycleOptions = JSON.parse(root.formController.lifecycleOptionsJson())
        root.connectionOptions = JSON.parse(root.formController.connectionOptionsJson())
        root.serverOptions = JSON.parse(root.formController.serverOptionsJson())
        root.linkOptions = JSON.parse(root.formController.linkOptionsJson())
        root.controlImplOptions = JSON.parse(root.formController.controlImplOptionsJson())
        root.resolutionOptions = JSON.parse(root.formController.resolutionOptionsJson())
        root.challengeCharacters = JSON.parse(root.formController.challengeCharactersJson())
        root.challengeAwards = JSON.parse(root.formController.challengeAwardsJson())
        root.eventShopItems = JSON.parse(root.formController.eventShopItemsJson())
    }

    Component.onCompleted: {
        root.reloadOptions()
        root.refreshValidation()
    }

    Connections {
        target: root.formController

        function onConfigChanged() { root.refreshValidation() }
        function onDirtyChanged(value) { root.dirty = !!value; root.refreshValidation() }
        function onConfigSwitched() { root.refreshValidation() }
        function onEmulatorInstancesReady(emulatorType, json) {
            root.handleInstancesReady(emulatorType, json)
        }
        function onOperationSucceeded(msg) { App.Notice.show("success", msg) }
        function onOperationFailed(msg) {
            root.refreshValidation()
            App.Notice.show("error", msg)
        }
    }

    // 切换设备类型时清空实例列表并触发重新枚举
    Connections {
        target: root
        function onLcTypeChanged() {
            root.mumuInstances = []
            root.avdInstances = []
            if (root.isMumu) root.refreshMumuInstances()
            else if (root.lcType === "avd") root.refreshAvdInstances()
        }
    }

    // 语言切换后重新拉取 Python 侧下发的选项文本与实例列表占位项
    Connections {
        target: App.Globals
        function onLanguageChanged() {
            root.reloadOptions()
            if (root.isMumu) root.refreshMumuInstances()
            else if (root.lcType === "avd") root.refreshAvdInstances()
        }
    }

    ScrollView {
        id: scrollView
        anchors.fill: parent
        enabled: !root.scriptRunning
        clip: true
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        ColumnLayout {
            width: scrollView.availableWidth
            spacing: 12

            // ── 游戏设置 ────────────────────────────────────────────────
            FormGroupBox {
                title: App.Globals.t("settings.group.game")
                FormSegmentedButton {
                    label: App.Globals.t("settings.field.game.server")
                    binder: formB
                    field: "game.server"
                    options: root.serverOptions
                    help: App.Globals.t("settings.help.server")
                }
                FormSegmentedButton {
                    label: App.Globals.t("settings.field.game.link_account")
                    binder: formB
                    field: "game.link_account"
                    options: root.linkOptions
                    visible: root.config.game && root.config.game.server === "jp"
                    help: App.Globals.t("settings.help.link_account")
                }
            }

            // ── 设备设置 ────────────────────────────────────────────────
            FormGroupBox {
                title: App.Globals.t("settings.group.device")
                FormSegmentedButton {
                    label: App.Globals.t("settings.field.device.lifecycle_type")
                    options: root.lifecycleOptions
                    value: root.lcType
                    onUserSelected: function(v) { root.setLifecycleType(v) }
                }
                FormInstancePicker {
                    label: App.Globals.t("settings.field.device.mumu_instance")
                    binder: lcB
                    field: "instance_id"
                    visible: root.isMumu
                    options: root.mumuInstances
                    loading: root.mumuEnumerationLoading
                    onRefreshTriggered: root.refreshMumuInstances()
                }
                FormTextField {
                    label: App.Globals.t("settings.field.device.sdk_path")
                    binder: lcB
                    field: "sdk_path"
                    visible: root.lcType === "avd"
                    placeholder: App.Globals.t("settings.placeholder.sdk_path")
                    help: App.Globals.t("settings.help.sdk_path")
                }
                FormTextField {
                    label: App.Globals.t("settings.field.device.extra_args")
                    binder: lcB
                    field: "extra_args"
                    visible: root.lcType === "avd"
                    placeholder: App.Globals.t("settings.placeholder.extra_args")
                    help: App.Globals.t("settings.help.extra_args")
                }
                FormInstancePicker {
                    label: App.Globals.t("settings.field.device.avd_instance")
                    binder: lcB
                    field: "avd_name"
                    visible: root.lcType === "avd"
                    options: root.avdInstances
                    loading: root.avdEnumerationLoading
                    onRefreshTriggered: root.refreshAvdInstances()
                }
                FormCheckBox {
                    label: App.Globals.t("settings.field.device.check_and_start")
                    binder: lcB
                    field: "check_and_start"
                    visible: root.hasLifecycle
                }
                FormCheckBox {
                    label: App.Globals.t("settings.field.device.stop_on_finish")
                    binder: formB
                    field: "device.stop_on_finish"
                    visible: root.hasLifecycle && root.lcCheckAndStart
                    help: App.Globals.t("settings.help.stop_on_finish")
                }
                FormTextField {
                    label: App.Globals.t("settings.field.device.custom_start_command")
                    binder: lcB
                    field: "start_command"
                    visible: root.lcType === "custom"
                    help: App.Globals.t("settings.help.custom_start_command")
                }
                FormCheckBox {
                    label: App.Globals.t("settings.field.device.custom_wait_start_command")
                    binder: lcB
                    field: "wait_start_command"
                    visible: root.lcType === "custom"
                }
                FormTextField {
                    label: App.Globals.t("settings.field.device.custom_stop_command")
                    binder: lcB
                    field: "stop_command"
                    visible: root.lcType === "custom"
                    placeholder: App.Globals.t("settings.placeholder.custom_stop_command")
                }
                FormTextField {
                    label: App.Globals.t("settings.field.device.custom_running_command")
                    binder: lcB
                    field: "running_command"
                    visible: root.lcType === "custom"
                    placeholder: App.Globals.t("settings.placeholder.custom_running_command")
                }
            }

            // ── 连接设置 ────────────────────────────────────────────────
            FormGroupBox {
                title: App.Globals.t("settings.group.connection")
                visible: root.showConnectionSection
                FormSegmentedButton {
                    label: App.Globals.t("settings.field.device.connection_type")
                    options: root.connectionOptions
                    value: root.connType
                    onUserSelected: function(v) { root.setConnectionType(v) }
                }
                FormTextField {
                    label: App.Globals.t("settings.field.device.serial")
                    binder: connB
                    field: "device_serial"
                    visible: root.connType === "usb"
                    placeholder: App.Globals.t("settings.placeholder.usb_serial")
                }
                FormTextField {
                    label: App.Globals.t("settings.field.device.tcp_ip")
                    binder: connB
                    field: "ip"
                    visible: root.connType === "tcp"
                }
                FormTextField {
                    label: App.Globals.t("settings.field.device.tcp_port")
                    binder: connB
                    field: "port"
                    visible: root.connType === "tcp"
                }
                FormCheckBox {
                    label: App.Globals.t("settings.field.device.tcp_run_adb_connect")
                    binder: connB
                    field: "run_adb_connect"
                    visible: root.connType === "tcp"
                    help: App.Globals.t("settings.help.tcp_run_adb_connect")
                }
                FormTextField {
                    label: App.Globals.t("settings.field.device.serial")
                    binder: connB
                    field: "device_serial"
                    visible: root.connType === "tcp"
                    placeholder: App.Globals.t("settings.placeholder.tcp_device_serial")
                }
            }

            // ── 控制方式 ────────────────────────────────────────────────
            FormGroupBox {
                title: App.Globals.t("settings.group.control")
                visible: root.lcType !== "playcover"
                FormSegmentedButton {
                    label: App.Globals.t("settings.field.device.control_impl")
                    binder: formB
                    field: "device.control_impl"
                    options: root.controlImplOptionsForLc
                    help: App.Globals.t("settings.help.control_impl")
                }
                FormNotice {
                    style: "tip"
                    content: App.Globals.t("settings.notice.nemu_ipc_tip")
                    visible: root.isMumu && root.controlImpl !== "nemu_ipc"
                }
                FormCheckBox {
                    label: App.Globals.t("settings.field.device.scrcpy_virtual_display")
                    binder: formB
                    field: "device.scrcpy_virtual_display"
                    visible: root.controlImpl === "scrcpy"
                }
                FormResolutionSelect {
                    label: App.Globals.t("settings.field.device.resolution_method")
                    binder: formB
                    field: "device.resolution_method"
                    options: root.resolutionOptionsForImpl
                    enabled: root.controlImpl !== "qemu_grpc"
                    resetEnabled: root.controlImpl !== "qemu_grpc"
                    onResetRequested: root.formController.resetResolution()
                    help: App.Globals.t("settings.help.resolution_method")
                }
                FormNotice {
                    style: "warning"
                    content: App.Globals.t("settings.notice.resolution_wm_size_warning")
                    visible: root.controlImpl !== "qemu_grpc" && root.formController.config?.device?.resolution_method === "wm_size"
                }
                FormNotice {
                    style: "tip"
                    content: App.Globals.t("settings.notice.qemu_grpc_resolution_tip")
                    visible: root.lcType === "avd" && root.controlImpl === "qemu_grpc"
                }
            }

            // ── 演出设置 ────────────────────────────────────────────────
            FormGroupBox {
                title: App.Globals.t("settings.group.live")
                FormComboBox {
                    label: App.Globals.t("settings.field.live.song_name")
                    options: root.songNameOptions
                    value: (root.config.tasks && root.config.tasks.solo_live) ? (root.config.tasks.solo_live.song_name || "保持不变") : "保持不变"
                    onUserSelected: function(v) {
                        root.formController.setField("tasks.solo_live.song_name", v === "保持不变" ? null : v)
                    }
                }
                FormComboBox {
                    label: App.Globals.t("settings.field.live.ap_multiplier")
                    options: root.apMultiplierOptions
                    value: (root.config.tasks && root.config.tasks.solo_live && root.config.tasks.solo_live.ap_multiplier !== null && root.config.tasks.solo_live.ap_multiplier !== undefined)
                        ? String(root.config.tasks.solo_live.ap_multiplier)
                        : "保持现状"
                    onUserSelected: function(v) {
                        root.formController.setField("tasks.solo_live.ap_multiplier", v === "保持现状" ? null : (v === "maximum" ? "maximum" : parseInt(v, 10)))
                    }
                }
                FormCheckBox {
                    label: App.Globals.t("settings.field.live.auto_set_unit")
                    binder: formB
                    field: "tasks.solo_live.auto_set_unit"
                }
                FormCheckBox {
                    label: App.Globals.t("settings.field.live.append_fc")
                    binder: formB
                    field: "tasks.solo_live.append_fc"
                }
                FormCheckBox {
                    label: App.Globals.t("settings.field.live.append_random")
                    binder: formB
                    field: "tasks.solo_live.prepend_random"
                }
            }

            // ── 挑战演出设置 ────────────────────────────────────────────
            FormGroupBox {
                title: App.Globals.t("settings.group.challenge_live")
                FormIconItemPicker {
                    label: App.Globals.t("settings.field.challenge.characters")
                    binder: formB
                    field: "tasks.challenge_live.characters"
                    options: root.challengeCharacters
                    singleToArray: true
                    cellSize: 100
                    iconSize: 70
                }
                FormIconItemPicker {
                    label: App.Globals.t("settings.field.challenge.award")
                    binder: formB
                    field: "tasks.challenge_live.award"
                    options: root.challengeAwards
                    cellSize: 80
                    iconSize: 56
                }
            }

            // ── CM 设置 ─────────────────────────────────────────────────
            FormGroupBox {
                title: App.Globals.t("settings.group.cm")
                FormTextField {
                    label: App.Globals.t("settings.field.cm.watch_ad_wait_sec")
                    binder: formB
                    field: "tasks.cm.watch_ad_wait_sec"
                }
            }

            // ── 活动商店设置 ────────────────────────────────────────────
            FormGroupBox {
                title: App.Globals.t("settings.group.event_shop")
                FormSortableChecklist {
                    label: App.Globals.t("settings.field.event_shop.purchase_items")
                    binder: formB
                    field: "tasks.event_shop.purchase_items"
                    options: root.eventShopItems
                    Layout.preferredHeight: 300
                }
            }

            // ── 调度设置 ────────────────────────────────────────────────
            FormGroupBox {
                title: App.Globals.t("settings.group.scheduler")
                FormCheckBox {
                    label: App.Globals.t("settings.field.scheduler.continue_on_error")
                    binder: formB
                    field: "scheduler.continue_on_error"
                }
            }

            // ── 开发者设置 ──────────────────────────────────────────────
            FormGroupBox {
                title: App.Globals.t("settings.group.developer")
                FormCheckBox {
                    label: App.Globals.t("settings.field.developer.dump_sekai_home")
                    binder: formB
                    field: "developer.dump_sekai_home_enabled"
                }
                FormCheckBox {
                    label: App.Globals.t("settings.field.developer.sekai_dump_post_process")
                    binder: formB
                    field: "developer.sekai_dump_post_process"
                }
                FormCheckBox {
                    label: App.Globals.t("settings.field.developer.screen_recording")
                    binder: formB
                    field: "developer.screen_recording_enabled"
                    help: App.Globals.t("settings.help.screen_recording")
                }
            }
        }
    }
}
