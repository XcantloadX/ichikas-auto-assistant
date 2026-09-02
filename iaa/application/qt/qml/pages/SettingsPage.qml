pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../components"
import "../components/form"
import ".." as App

// 设置页：QML 直写表单（kaa 风格）。表单定义直接声明在这里，
// 通过 FormBinder 与 SettingsController.config（base+dirty 草稿视图）双向绑定，
// setField 写入草稿，save 归一化 + 校验 + 写盘。
PageContainer {
    id: root
    title: "配置"

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
                text: "脚本运行时无法修改配置"
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
                text: "有未保存改动"
                color: "#DC3545"
                font.bold: true
                anchors.centerIn: parent
            }
        }
    }

    headerActions: Button {
        text: "保存"
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
        {label: "保持不变", value: "保持不变"},
        {label: "メルト", value: "メルト"},
        {label: "独りんぼエンヴィー", value: "独りんぼエンヴィー"}
    ]
    readonly property var apMultiplierOptions: [
        {label: "保持现状", value: "保持现状"},
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
            return [{value: "keep", label: "保持原始分辨率"}]
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

    Component.onCompleted: {
        root.lifecycleOptions = JSON.parse(root.formController.lifecycleOptionsJson())
        root.connectionOptions = JSON.parse(root.formController.connectionOptionsJson())
        root.serverOptions = JSON.parse(root.formController.serverOptionsJson())
        root.linkOptions = JSON.parse(root.formController.linkOptionsJson())
        root.controlImplOptions = JSON.parse(root.formController.controlImplOptionsJson())
        root.resolutionOptions = JSON.parse(root.formController.resolutionOptionsJson())
        root.challengeCharacters = JSON.parse(root.formController.challengeCharactersJson())
        root.challengeAwards = JSON.parse(root.formController.challengeAwardsJson())
        root.eventShopItems = JSON.parse(root.formController.eventShopItemsJson())
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
                title: "游戏设置"
                FormSegmentedButton {
                    label: "服务器"
                    binder: formB
                    field: "game.server"
                    options: root.serverOptions
                    help: "广告：现招募维护者维护除日服以外的服务器适配~ 如果你有兴趣参与维护，请联系作者。<hr>维护者：<ul><li>日服：作者本人</li><li>台服：空缺</li><li>国服：空缺</li><li>国际服：空缺</li><li>韩服：空缺</li></ul>"
                }
                FormSegmentedButton {
                    label: "引继账号"
                    binder: formB
                    field: "game.link_account"
                    options: root.linkOptions
                    visible: root.config.game && root.config.game.server === "jp"
                    help: "每次启动游戏的时候是否使用引继账号登录（仅限日服）"
                }
            }

            // ── 设备设置 ────────────────────────────────────────────────
            FormGroupBox {
                title: "设备设置"
                FormSegmentedButton {
                    label: "设备类型"
                    options: root.lifecycleOptions
                    value: root.lcType
                    onUserSelected: function(v) { root.setLifecycleType(v) }
                }
                FormInstancePicker {
                    label: "多开实例"
                    binder: lcB
                    field: "instance_id"
                    visible: root.isMumu
                    options: root.mumuInstances
                    loading: root.mumuEnumerationLoading
                    onRefreshTriggered: root.refreshMumuInstances()
                }
                FormTextField {
                    label: "SDK 路径"
                    binder: lcB
                    field: "sdk_path"
                    visible: root.lcType === "avd"
                    placeholder: "留空自动查找"
                    help: "Android SDK 路径。自动查找顺序：<ol><li>环境变量 <code>ANDROID_HOME</code> / <code>ANDROID_SDK_ROOT</code></li><li>Windows：<code>%LOCALAPPDATA%\\Android\\Sdk</code></li><li>macOS：<code>~/Library/Android/sdk</code></li><li>Linux：<code>~/Android/Sdk</code></li><li><code>PATH</code> 中的 <code>emulator</code></li></ol>填写后将只在该目录下查找，忽略以上自动查找逻辑。"
                }
                FormTextField {
                    label: "额外启动参数"
                    binder: lcB
                    field: "extra_args"
                    visible: root.lcType === "avd"
                    placeholder: "可选，例如 -gpu swiftshader_indirect -no-audio"
                    help: "追加到 emulator 命令行末尾的参数，以空格分隔。"
                }
                FormInstancePicker {
                    label: "AVD 实例"
                    binder: lcB
                    field: "avd_name"
                    visible: root.lcType === "avd"
                    options: root.avdInstances
                    loading: root.avdEnumerationLoading
                    onRefreshTriggered: root.refreshAvdInstances()
                }
                FormCheckBox {
                    label: "检查并启动"
                    binder: lcB
                    field: "check_and_start"
                    visible: root.hasLifecycle
                }
                FormCheckBox {
                    label: "完成后关闭模拟器"
                    binder: formB
                    field: "device.stop_on_finish"
                    visible: root.hasLifecycle && root.lcCheckAndStart
                    help: "所有任务执行完毕后，自动停止由 iaa 本次启动的模拟器。若模拟器在启动前已在运行，则不会关闭。"
                }
                FormTextField {
                    label: "启动命令"
                    binder: lcB
                    field: "start_command"
                    visible: root.lcType === "custom"
                    help: "将会通过 shell 方式执行。因此编写时请注意转义等问题。<br>下面两个命令也是一样的。"
                }
                FormCheckBox {
                    label: "等待启动命令退出后才继续"
                    binder: lcB
                    field: "wait_start_command"
                    visible: root.lcType === "custom"
                }
                FormTextField {
                    label: "结束命令"
                    binder: lcB
                    field: "stop_command"
                    visible: root.lcType === "custom"
                    placeholder: "可选。如果为空，将会自动终止启动命令中的进程"
                }
                FormTextField {
                    label: "运行检测命令"
                    binder: lcB
                    field: "running_command"
                    visible: root.lcType === "custom"
                    placeholder: "可选。如果为空，将会使用默认的运行检测方式"
                }
            }

            // ── 连接设置 ────────────────────────────────────────────────
            FormGroupBox {
                title: "连接设置"
                visible: root.showConnectionSection
                FormSegmentedButton {
                    label: "连接方式"
                    options: root.connectionOptions
                    value: root.connType
                    onUserSelected: function(v) { root.setConnectionType(v) }
                }
                FormTextField {
                    label: "设备序列号"
                    binder: connB
                    field: "device_serial"
                    visible: root.connType === "usb"
                    placeholder: "留空自动选择第一个 USB 设备"
                }
                FormTextField {
                    label: "ADB IP"
                    binder: connB
                    field: "ip"
                    visible: root.connType === "tcp"
                }
                FormTextField {
                    label: "ADB 端口"
                    binder: connB
                    field: "port"
                    visible: root.connType === "tcp"
                }
                FormCheckBox {
                    label: "执行 adb connect"
                    binder: connB
                    field: "run_adb_connect"
                    visible: root.connType === "tcp"
                    help: "如果需要通过「IP:端口」的形式连接设备，需要勾选。"
                }
                FormTextField {
                    label: "设备序列号"
                    binder: connB
                    field: "device_serial"
                    visible: root.connType === "tcp"
                    placeholder: "留空则默认使用 IP:端口 作为序列号"
                }
            }

            // ── 控制方式 ────────────────────────────────────────────────
            FormGroupBox {
                title: "控制方式"
                visible: root.lcType !== "playcover"
                FormSegmentedButton {
                    label: "控制方式"
                    binder: formB
                    field: "device.control_impl"
                    options: root.controlImplOptionsForLc
                    help: "对于 MuMu 模拟器，推荐使用 <b>Nemu IPC</b> 方式；对于 AVD，推荐使用 <b>QEMU gRPC</b>（直接读取模拟器帧缓冲，速度最快）或 <b>ADB</b>；对于其他模拟器与物理机，推荐使用 <b>Scrcpy</b> 方式"
                }
                FormNotice {
                    style: "tip"
                    content: "MuMu 模拟器选择 NemuIPC 效果最佳"
                    visible: root.isMumu && root.controlImpl !== "nemu_ipc"
                }
                FormCheckBox {
                    label: "使用虚拟显示器"
                    binder: formB
                    field: "device.scrcpy_virtual_display"
                    visible: root.controlImpl === "scrcpy"
                }
                FormResolutionSelect {
                    label: "分辨率设置"
                    binder: formB
                    field: "device.resolution_method"
                    options: root.resolutionOptionsForImpl
                    enabled: root.controlImpl !== "qemu_grpc"
                    resetEnabled: root.controlImpl !== "qemu_grpc"
                    onResetRequested: root.formController.resetResolution()
                    help: "<b>保持原始分辨率</b>：不做任何修改。<br><b>强制修改分辨率</b>：对所有设备执行 <code>wm size</code>。"
                }
                FormNotice {
                    style: "warning"
                    content: "警告！<b>强制修改分辨率可能导致设备无法正常使用且无法恢复！</b>务必阅读<a href=\"https://p.kdocs.cn/s/AGBH56RBAAAFS?linkname=WKAL5qgRTi\">此处</a>说明后才使用该功能。"
                    visible: root.controlImpl !== "qemu_grpc" && root.formController.config?.device?.resolution_method === "wm_size"
                }
                FormNotice {
                    style: "tip"
                    content: "使用 QEMU gRPC 控制方式时，请在 Android Studio AVD Manager 中预先将分辨率配置为 1280x720。"
                    visible: root.lcType === "avd" && root.controlImpl === "qemu_grpc"
                }
            }

            // ── 演出设置 ────────────────────────────────────────────────
            FormGroupBox {
                title: "演出设置"
                FormComboBox {
                    label: "歌曲名称"
                    options: root.songNameOptions
                    value: (root.config.tasks && root.config.tasks.solo_live) ? (root.config.tasks.solo_live.song_name || "保持不变") : "保持不变"
                    onUserSelected: function(v) {
                        root.formController.setField("tasks.solo_live.song_name", v === "保持不变" ? null : v)
                    }
                }
                FormComboBox {
                    label: "AP 倍率"
                    options: root.apMultiplierOptions
                    value: (root.config.tasks && root.config.tasks.solo_live && root.config.tasks.solo_live.ap_multiplier !== null && root.config.tasks.solo_live.ap_multiplier !== undefined)
                        ? String(root.config.tasks.solo_live.ap_multiplier)
                        : "保持现状"
                    onUserSelected: function(v) {
                        root.formController.setField("tasks.solo_live.ap_multiplier", v === "保持现状" ? null : parseInt(v, 10))
                    }
                }
                FormCheckBox {
                    label: "自动编队"
                    binder: formB
                    field: "tasks.solo_live.auto_set_unit"
                }
                FormCheckBox {
                    label: "追加一次 FullCombo 演出"
                    binder: formB
                    field: "tasks.solo_live.append_fc"
                }
                FormCheckBox {
                    label: "追加一首随机歌曲"
                    binder: formB
                    field: "tasks.solo_live.prepend_random"
                }
            }

            // ── 挑战演出设置 ────────────────────────────────────────────
            FormGroupBox {
                title: "挑战演出设置"
                FormIconItemPicker {
                    label: "角色"
                    binder: formB
                    field: "tasks.challenge_live.characters"
                    options: root.challengeCharacters
                    singleToArray: true
                    cellSize: 100
                    iconSize: 70
                }
                FormIconItemPicker {
                    label: "奖励"
                    binder: formB
                    field: "tasks.challenge_live.award"
                    options: root.challengeAwards
                    cellSize: 80
                    iconSize: 56
                }
            }

            // ── CM 设置 ─────────────────────────────────────────────────
            FormGroupBox {
                title: "CM 设置"
                FormTextField {
                    label: "广告等待秒数"
                    binder: formB
                    field: "tasks.cm.watch_ad_wait_sec"
                }
            }

            // ── 活动商店设置 ────────────────────────────────────────────
            FormGroupBox {
                title: "活动商店设置"
                FormSortableChecklist {
                    label: "购买项"
                    binder: formB
                    field: "tasks.event_shop.purchase_items"
                    options: root.eventShopItems
                    Layout.preferredHeight: 300
                }
            }

            // ── 调度设置 ────────────────────────────────────────────────
            FormGroupBox {
                title: "调度设置"
                FormCheckBox {
                    label: "错误时继续执行后续任务"
                    binder: formB
                    field: "scheduler.continue_on_error"
                }
            }

            // ── 开发者设置 ──────────────────────────────────────────────
            FormGroupBox {
                title: "开发者设置（仅供开发使用！）"
                FormCheckBox {
                    label: "dump 烤森"
                    binder: formB
                    field: "developer.dump_sekai_home_enabled"
                }
                FormCheckBox {
                    label: "dump 烤森 - 后处理与预打标"
                    binder: formB
                    field: "developer.sekai_dump_post_process"
                }
                FormCheckBox {
                    label: "自动录屏（需安装 ffmpeg）"
                    binder: formB
                    field: "developer.screen_recording_enabled"
                    help: "脚本启动时自动录屏，结束时自动结束。输出到 dumps/screen_records/ 目录。"
                }
            }
        }
    }
}
