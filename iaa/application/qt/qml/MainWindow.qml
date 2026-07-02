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
            title: App.Globals.t("modal.telemetry.title"),
            content: App.Globals.t("modal.telemetry.content"),
            buttons: [
                { text: App.Globals.t("modal.telemetry.deny"), value: "deny" },
                { text: App.Globals.t("modal.telemetry.allow"), value: "allow", highlighted: true }
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
        var closeRunner = function() {
            window.allowImmediateClose = true
            window.close()
        }
        if (window.runCtrl && window.runCtrl.running) {
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
                // App.Globals.t("nav.help"),
                App.Globals.t("nav.about")
            ]
            currentConfig: App.ProfileStore.currentProfileName

            onCurrentChanging: function(index, previousIndex) {
                navigation.requestGuardedAction(App.Globals.t("guard.switch_page"), function() {
                    sideNav.confirmSwitch(index)
                })
            }

            onProfileSwitchRequested: function(name) {
                navigation.requestGuardedAction(App.Globals.t("guard.switch_config"), function() {
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

            // HelpPage {
            //     id: helpPage
            // }

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
