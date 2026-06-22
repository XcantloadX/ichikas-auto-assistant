import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "." as App
import "pages"
import "dialogs"

import "components"

ApplicationWindow {
    id: window
    width: 1100
    height: 680
    visible: true
    title: window.appCtrl ? window.appCtrl.windowTitle : ""
    font.family: Qt.platform.os === "windows"
        ? "Microsoft YaHei UI"
        : Qt.platform.os === "osx"
            ? "PingFang SC"
            : "Noto Sans CJK SC"

    readonly property var appCtrl: appController
    readonly property var runCtrl: runController
    readonly property var settingsCtrl: settingsController
    readonly property var prefsCtrl: preferencesController
    readonly property var logBridgeObj: logBridge
    property bool allowImmediateClose: false

    function requestTelemetryConsent() {
        App.Modal.message({
            title: "数据收集",
            content: "是否允许 iaa 自动发送匿名错误报告？发送的信息仅用于改善 iaa。",
            buttons: [
                { text: "拒绝", value: "deny" },
                { text: "允许", value: "allow", highlighted: true }
            ],
            width: 420,
            closePolicy: Popup.NoAutoClose
        }, function(result) {
            if (!window.appCtrl) {
                return
            }
            if (result === "allow") {
                window.appCtrl.setTelemetryConsent(true)
            }
            if (result === "deny") {
                window.appCtrl.setTelemetryConsent(false)
            }
        })
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
        var closeRunner = function() {
            window.allowImmediateClose = true
            window.close()
        }
        if (window.runCtrl && window.runCtrl.running) {
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
        settingsCtrl: window.settingsCtrl
        prefsCtrl: window.prefsCtrl
        unsavedChangesDialog: unsavedChangesDialog
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        SideNavigationBar {
            id: sideNav
            Layout.fillHeight: true
            model: [
                App.Globals.t("nav.control"),
                App.Globals.t("nav.config"),
                App.Globals.t("nav.preferences"),
                App.Globals.t("nav.logs"),
                App.Globals.t("nav.about")
            ]
            currentConfig: App.ProfileStore.currentProfileName

            onCurrentChanging: function(index, previousIndex) {
                navigation.requestGuardedAction("切换页面", function() {
                    sideNav.confirmSwitch(index)
                })
            }

            onProfileSwitchRequested: function(name) {
                navigation.requestGuardedAction("切换配置", function() {
                    window.settingsCtrl.switchProfile(name)
                })
            }

            onOpenConfigManager: {
                configManagerDialog.open()
            }
        }

        StackLayout {
            id: stack
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: sideNav.currentIndex

            ControlPage {
                id: controlPage
                autoLiveDialog: autoLiveDialogView
            }

            SettingsPage {
                id: settingsPage
                formController: window.settingsCtrl
            }

            PreferencesPage {
                id: preferencesPage
                prefsController: window.prefsCtrl
            }

            LogPage {
                id: logPage
                logBridge: window.logBridgeObj
            }

            // HelpPage {}

            AboutPage {}
        }
    }

    AutoLiveDialog {
        id: autoLiveDialogView
    }

    ConfigManagerDialog {
        id: configManagerDialog
        navigation: navigation
        settingsCtrl: window.settingsCtrl
    }

    ModalHost {
        id: modalHost
    }

    NoticeHost {
        id: noticeHost
    }

    // ScrcpyWindow {}


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
        function onTelemetryConsentRequiredChanged() {
            if (window.appCtrl && window.appCtrl.telemetryConsentRequired) {
                window.requestTelemetryConsent()
            }
        }
    }

    Connections {
        target: window.runCtrl
        function onScriptAutoWarningRequested(text) {
            App.Notice.show("error", text)
        }
    }

    Component.onCompleted: {
        if (window.appCtrl && window.appCtrl.telemetryConsentRequired) {
            window.requestTelemetryConsent()
        }
        if (window.appCtrl) {
            var migrationMsg = window.appCtrl.checkMigrationMessages()
            if (migrationMsg) {
                window.showMigrationMessage(migrationMsg)
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
        if (window.runCtrl && window.runCtrl.running) {
            window.requestAppClose()
            return
        }
        window.requestAppClose()
    }
}
