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
            title: App.Globals.t("modal.migration.title"),
            content: text,
            textFormat: Text.RichText,
            buttons: [
                { text: App.Globals.t("common.ok"), value: "ok", highlighted: true }
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
                title: App.Globals.t("modal.exit.title"),
                content: App.Globals.t("modal.exit.content"),
                buttons: [
                    { text: App.Globals.t("common.cancel"), value: "cancel" },
                    { text: App.Globals.t("modal.exit.confirm"), value: "ok", highlighted: true }
                ],
                width: 420,
                closePolicy: Popup.NoAutoClose
            }, function(result) {
                if (result === "ok") {
                    navigation.requestGuardedAction(App.Globals.t("guard.close_window"), closeRunner)
                }
            })
            return
        }
        navigation.requestGuardedAction(App.Globals.t("guard.close_window"), closeRunner)
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
        title: App.Globals.t("modal.unsaved.title")
        standardButtons: Dialog.NoButton
        width: Math.max(360, Math.min(540, window.width - 48))
        anchors.centerIn: Overlay.overlay

        property string actionLabel: App.Globals.t("common.continue_action")

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: App.Globals.t("modal.unsaved.content").replace("{action}", unsavedChangesDialog.actionLabel)
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Button {
                    Layout.fillWidth: true
                    Layout.minimumWidth: implicitWidth
                    Layout.preferredWidth: implicitWidth
                    text: App.Globals.t("common.cancel")
                    onClicked: {
                        navigation.clearPendingGuardedAction()
                        unsavedChangesDialog.close()
                    }
                }
                Button {
                    Layout.fillWidth: true
                    Layout.minimumWidth: implicitWidth
                    Layout.preferredWidth: implicitWidth
                    text: App.Globals.t("common.do_not_save_and_continue")
                    onClicked: {
                        unsavedChangesDialog.close()
                        navigation.discardAndContinuePendingAction()
                    }
                }
                Button {
                    Layout.fillWidth: true
                    Layout.minimumWidth: implicitWidth
                    Layout.preferredWidth: implicitWidth
                    text: App.Globals.t("common.save_and_continue")
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
                        text: App.Globals.t("common.copy"),
                        onClick: function() {
                            App.Clipboard.copyText(message)
                            App.Notice.show("success", App.Globals.t("notice.copied_to_clipboard"))
                        }
                    },
                    { text: App.Globals.t("common.ok"), highlighted: true, onClick: "close" }
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
            title: App.Globals.t("modal.config_reset.title"),
            content: App.Globals.t("modal.config_reset.content")
                .replace("{name}", configName)
                .replace("{fields}", fieldList)
                .replace("{details}", errorDetails),
            buttons: [
                { text: App.Globals.t("modal.config_reset.no_reset"), value: "cancel" },
                { text: App.Globals.t("modal.config_reset.reset"), value: "reset", highlighted: true }
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
        title: App.Globals.t("preferences.group.telemetry")
        modal: true
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: parent
        width: Math.min(420, window.width - 80)
        standardButtons: Dialog.NoButton

        Column {
            width: parent.width
            spacing: 10
            Text {
                text: App.Globals.t("modal.telemetry.content")
                font.pixelSize: 13
                color: palette.windowText
                wrapMode: Text.Wrap
                width: parent.width
                lineHeight: 1.4
            }

            Switch {
                id: staticsSwitch
                text: App.Globals.t("preferences.field.telemetry_statics")
                checked: true
            }

            Switch {
                id: sentrySwitch
                text: App.Globals.t("preferences.field.telemetry_sentry")
                checked: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 2

                Switch {
                    id: screenshotSwitch
                    text: App.Globals.t("preferences.field.telemetry_upload_screenshot")
                    checked: true
                }

                HelpTip {
                    richText: App.Globals.t("modal.telemetry.screenshot_help")
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
                    text: App.Globals.t("common.ok")
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
                    title: App.Globals.t("modal.path_warning.title"),
                    content: App.Globals.t("modal.path_warning.content"),
                    buttons: [
                        { text: App.Globals.t("common.ok"), value: "ok", highlighted: true }
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
