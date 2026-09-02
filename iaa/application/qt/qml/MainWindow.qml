import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "." as App
import "pages"
import "dialogs"
import "components"
import IaaApp 1.0

ApplicationWindow {
    id: window
    width: 1100
    height: 680
    visible: true
    title: window.appCtrl ? window.appCtrl.windowTitle : ""
    flags: Qt.platform.os === "windows"
        ? (Qt.Window | Qt.FramelessWindowHint)
        : Qt.Window
    font.family: Qt.platform.os === "windows"
        ? "Microsoft YaHei UI"
        : Qt.platform.os === "osx"
            ? "PingFang SC"
            : "Noto Sans CJK SC"

    // 加载 FluentSystemIcons-Regular（MIT），注册后全局可用 font.family: "FluentSystemIcons-Regular"
    FontLoader {
        source: Globals.assetPath("fonts/FluentSystemIcons-Regular.ttf")
    }

    readonly property var appCtrl: AppController
    readonly property var prefsCtrl: PreferencesController
    property bool allowImmediateClose: false
    property bool prefsMode: false
    property int _prevTitleBarIndex: 0

    function enterPrefsMode() {
        _prevTitleBarIndex = titleBar.currentIndex
        titleBar.setCurrentIndex(1)
        prefsMode = true
    }

    function exitPrefsMode() {
        prefsMode = false
        titleBar.setCurrentIndex(_prevTitleBarIndex)
    }

    // Per-tab 实例模型
    property var tabList: []
    property int activeTabIndex: 0
    property var activeSettingsCtrl: null   // 仅供 NavigationCoordinator / ConfigManagerDialog 使用

    // 仅在 tabs 增删时更新 tabList（避免 Repeater 模型重建）
    function _onTabsChanged() {
        tabList = JSON.parse(TabManager.tabsJson())
        activeTabIndex = TabManager.activeTabIndex
        activeSettingsCtrl = TabManager.activeSettingsController
        if (activeTabIndex >= 0) titleBar.setCurrentIndex(1)
    }

    // 切换 tab 时只更新 activeIndex，不碰 tabList（Repeater 模型保持不变）
    function _onActiveTabChanged() {
        activeTabIndex = TabManager.activeTabIndex
        activeSettingsCtrl = TabManager.activeSettingsController
        if (activeTabIndex < 0) titleBar.setCurrentIndex(0)
    }

    function navigateTo(pageKey, tabIndex) {
        if (pageKey === "tab") {
            titleBar.setCurrentIndex(1)
            if (tabIndex !== undefined) TabManager.setActiveTab(tabIndex)
        } else if (pageKey === "overview") {
            titleBar.setCurrentIndex(0)
        }
    }

    function requestTelemetryConsent() {
        telemetryConsentDialog.open()
    }

    function showMigrationMessage(text) {
        App.Modal.message({
            title: "配置升级",
            content: text,
            textFormat: Text.RichText,
            buttons: [
                { text: "确定", value: "ok", highlighted: true }
            ],
            width: 520
        })
    }

    function requestAppClose() {
        var anyRunning = TabManager.anyRunning
        var closeRunner = function() {
            window.allowImmediateClose = true
            window.close()
        }
        if (anyRunning) {
            App.Modal.message({
                title: "确认退出",
                content: "当前仍在执行任务，确定要退出吗？退出将先停止任务。",
                buttons: [
                    { text: "取消", value: "cancel" },
                    { text: "退出", value: "ok", highlighted: true }
                ],
                width: 420,
                closePolicy: Popup.NoAutoClose
            }, function(result) {
                if (result === "ok") {
                    navigation.requestGuardedAction("关闭窗口", closeRunner)
                }
            })
            return
        }
        navigation.requestGuardedAction("关闭窗口", closeRunner)
    }

    NavigationCoordinator {
        id: navigation
        settingsCtrl: window.activeSettingsCtrl
        prefsCtrl: window.prefsCtrl
        unsavedChangesDialog: unsavedChangesDialog
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        TitleBar {
            id: titleBar
            Layout.fillWidth: true
            configManagerDialog: configManagerDialog
            prefsMode: window.prefsMode
            onSettingsRequested: window.enterPrefsMode()
            onBackRequested: window.exitPrefsMode()
            onMinimizeRequested: window.showMinimized()
            onCloseRequested: window.requestAppClose()
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: titleBar.currentIndex

            // ── index 0：总览页 ─────────────────────────────────────
            OverviewPage {
                configManagerDialog: configManagerDialog
            }

            // ── index 1：per-tab 内容区 ─────────────────────────────
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                StackLayout {
                    anchors.fill: parent
                    currentIndex: window.activeTabIndex

                    Repeater {
                        id: tabContentRepeater
                        model: window.tabList
                        delegate: TabContent {
                            required property int index
                            runCtrl: TabManager.runControllerAt(index)
                            progBridge: TabManager.progressBridgeAt(index)
                            logBridge: TabManager.logBridgeAt(index)
                            formController: TabManager.settingsControllerAt(index)
                            navigation: navigation
                            prefsMode: window.prefsMode
                        }
                    }
                }

                // ── 偏好设置（全局单例，模式驱动，覆盖整个内容区）──────────────────────────
                PreferencesPage {
                    id: preferencesPage
                    anchors.fill: parent
                    visible: window.prefsMode
                    prefsController: window.prefsCtrl
                }
            }
        }
    }

    ConfigManagerDialog {
        id: configManagerDialog
        navigation: navigation
        settingsCtrl: window.activeSettingsCtrl
        tabManager: TabManager
    }

    ModalHost {
        id: modalHost
    }

    NoticeHost {
        id: noticeHost
    }

    Dialog {
        id: unsavedChangesDialog
        modal: true
        title: "未保存更改"
        standardButtons: Dialog.NoButton
        width: 420
        anchors.centerIn: Overlay.overlay

        property string actionLabel: "继续此操作"

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: "当前配置有未保存的更改。" + unsavedChangesDialog.actionLabel + "前，请先选择处理方式。"
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: 8
                Button {
                    text: "取消"
                    onClicked: {
                        navigation.clearPendingGuardedAction()
                        unsavedChangesDialog.close()
                    }
                }
                Button {
                    text: "不保存并继续"
                    onClicked: {
                        unsavedChangesDialog.close()
                        navigation.discardAndContinuePendingAction()
                    }
                }
                Button {
                    text: "保存并继续"
                    highlighted: true
                    onClicked: {
                        unsavedChangesDialog.close()
                        navigation.saveAndContinuePendingAction()
                    }
                }
            }
        }
    }

    Connections {
        target: window.appCtrl
        function onNotificationRaised(kind, text) {
            App.Notice.show(kind, text)
        }
        function onErrorDialogRequested(title, message) {
            App.Modal.custom({
                title: title,
                content: message,
                buttons: [
                    {
                        text: "复制",
                        onClick: function() {
                            App.Clipboard.copyText(message)
                            App.Notice.show("success", "已复制到剪贴板")
                        }
                    },
                    { text: "确定", highlighted: true, onClick: "close" }
                ]
            })
        }
        function onTelemetryConsentRequiredChanged() {
            if (window.appCtrl && window.appCtrl.telemetryConsentRequired) {
                window.requestTelemetryConsent()
            }
        }
    }

    function requestConfigReset(configName, invalidFieldsJson, errorDetails) {
        var fields = JSON.parse(invalidFieldsJson)
        var fieldList = fields.map(function(f) { return "&nbsp;&nbsp;• " + f }).join("<br>")
        App.Modal.message({
            title: "配置校验失败",
            content: "配置 <b>" + configName + "</b> 中以下字段校验失败：<br>"
                + fieldList
                + "<br><br>错误详情：<br>" + errorDetails
                + "<br><br>是否将这些字段重置为默认值？",
            buttons: [
                { text: "不重置", value: "cancel" },
                { text: "重置", value: "reset", highlighted: true }
            ],
            width: 480
        }, function(result) {
            if (result === "reset") {
                TabManager.resetAndOpenTab(configName, invalidFieldsJson)
            }
        })
    }

    // ── 匿名上报首次同意弹窗（启动时询问） ──────────────────────
    Dialog {
        id: telemetryConsentDialog
        title: "数据收集"
        modal: true
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: parent
        width: Math.min(420, window.width - 80)
        standardButtons: Dialog.NoButton

        Column {
            width: parent.width
            spacing: 10
            Text {
                text: "是否允许 iaa 自动发送匿名错误报告？发送的信息仅用于改善 iaa，你也可以随时在“设置”中更改。"
                font.pixelSize: 13
                color: palette.windowText
                wrapMode: Text.Wrap
                width: parent.width
                lineHeight: 1.4
            }

            Switch {
                id: staticsSwitch
                text: "匿名收集统计数据"
                checked: true
            }

            Switch {
                id: sentrySwitch
                text: "发送匿名错误报告"
                checked: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 2

                Switch {
                    id: screenshotSwitch
                    text: "错误上报时附带游戏截图"
                    checked: true
                }

                HelpTip {
                    richText: "只包含游戏画面截图，不含电脑桌面或其他应用内容。<br>如果不希望发送截图，请关闭此选项。"
                    Layout.alignment: Qt.AlignVCenter
                }
            }
        }

        footer: Rectangle {
            implicitHeight: 65
            color: palette.window
            Rectangle {
                width: parent.width; height: 1
                color: palette.windowText
                opacity: 0.12
            }
            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: 24
                spacing: 8
                Button {
                    text: "确定"
                    highlighted: true
                    onClicked: {
                        if (window.appCtrl) {
                            window.appCtrl.setTelemetryConsent(
                                sentrySwitch.checked,
                                screenshotSwitch.checked,
                                staticsSwitch.checked
                            )
                        }
                        telemetryConsentDialog.close()
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        _onTabsChanged()
        TabManager.tabsChanged.connect(window._onTabsChanged)
        TabManager.activeTabChanged.connect(window._onActiveTabChanged)

        // 根据 startup_page 设置决定初始页面（无 tab 时保持总览）
        if (window.appCtrl && window.appCtrl.startupPage === "last_opened" && window.tabList.length > 0) {
            titleBar.setCurrentIndex(1)
        }
        TabManager.scriptAutoWarningRequested.connect(function(text) {
            App.Notice.show("error", text)
        })
        TabManager.configValidationFailed.connect(window.requestConfigReset)
        if (window.appCtrl && window.appCtrl.telemetryConsentRequired) {
            window.requestTelemetryConsent()
        }
        if (window.appCtrl) {
            var migrationMsg = window.appCtrl.checkMigrationMessages()
            if (migrationMsg) {
                window.showMigrationMessage(migrationMsg)
            }
        }
        // 路径问题自检
        if (window.appCtrl) {
            var hasPathIssue = window.appCtrl.checkPathIssues()
            if (hasPathIssue) {
                App.Modal.message({
                    title: "提示",
                    content: "请勿将 iaa 放在 Program Files 程序文件夹下，以及 OneDrive 等云盘同步文件夹内，否则部分功能可能出现异常！",
                    buttons: [
                        { text: "确定", value: "ok", highlighted: true }
                    ],
                    width: 520
                })
            }
        }
    }

    onClosing: function(close) {
        if (window.allowImmediateClose) {
            window.allowImmediateClose = false
            close.accepted = window.appCtrl ? window.appCtrl.confirmClose() : true
            if (close.accepted) {
                if (window.appCtrl) {
                    window.appCtrl.shutdown()
                }
            }
            return
        }
        close.accepted = false
        var anyRunning = TabManager.anyRunning
        if (anyRunning) {
            window.requestAppClose()
            return
        }
        window.requestAppClose()
    }
}
