import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "." as App
import "pages"
import "dialogs"

import "components"

ApplicationWindow {
    id: window
    width: 980
    height: 680
    visible: true
    title: window.appCtrl ? window.appCtrl.windowTitle : ""
    font.family: "Microsoft YaHei UI"
    color: window.appCtrl && window.appCtrl.windowStyle === "solid" ? "#fff" : "transparent"
    background: null

    readonly property var appCtrl: appController
    readonly property var runCtrl: runController
    readonly property var settingsCtrl: settingsController
    readonly property var prefsCtrl: preferencesController
    property string noticeKind: "info"
    property string noticeText: ""
    property bool allowImmediateClose: false

    function showNotice(kind, text) {
        window.noticeKind = kind
        window.noticeText = text
        noticePopup.open()
    }

    function requestAppClose() {
        var closeRunner = function() {
            window.allowImmediateClose = true
            window.close()
        }
        if (window.runCtrl && window.runCtrl.running) {
            quitDialog.pendingCloseAction = closeRunner
            quitDialog.open()
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
            model: ["控制", "配置", "偏好", "关于"]
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
                onShowNotice: function(kind, text) { window.showNotice(kind, text) }
            }

            SettingsPage {
                id: settingsPage
                formController: window.settingsCtrl
                onShowNotice: function(kind, text) { window.showNotice(kind, text) }
            }

            PreferencesPage {
                id: preferencesPage
                prefsController: window.prefsCtrl
                onShowNotice: function(kind, text) { window.showNotice(kind, text) }
            }

            AboutPage {}
        }
    }

    AutoLiveDialog {
        id: autoLiveDialogView
        onShowNotice: function(kind, text) { window.showNotice(kind, text) }
    }

    ConfigManagerDialog {
        id: configManagerDialog
        navigation: navigation
        settingsCtrl: window.settingsCtrl
    }

    // ScrcpyWindow {}

    Popup {
        id: noticePopup
        x: parent.width - width - 24
        y: 24
        width: 360
        height: implicitHeight
        padding: 14
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle {
            radius: 8
            color: window.noticeKind === "error" ? "#7f1d1d" : "#14532d"
        }
        contentItem: Label {
            width: parent.width
            wrapMode: Text.Wrap
            color: "white"
            text: window.noticeText
        }
        onOpened: closeTimer.restart()
    }

    Timer {
        id: closeTimer
        interval: 4000
        onTriggered: noticePopup.close()
    }

    Dialog {
        id: telemetryDialog
        modal: true
        title: "数据收集"
        standardButtons: Dialog.NoButton
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: Overlay.overlay
        width: 420

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: "是否允许 iaa 自动发送匿名错误报告？发送的信息仅用于改善 iaa。"
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button {
                        text: "拒绝"
                    onClicked: {
                        window.appCtrl.setTelemetryConsent(false)
                        telemetryDialog.close()
                    }
                }
                Button {
                    text: "允许"
                    highlighted: true
                    onClicked: {
                        window.appCtrl.setTelemetryConsent(true)
                        telemetryDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: quitDialog
        modal: true
        title: "确认退出"
        standardButtons: Dialog.NoButton
        width: 420
        anchors.centerIn: Overlay.overlay
        property var pendingCloseAction: null
        background: null
        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: "当前仍在执行任务，确定要退出吗？退出将先停止任务。"
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button {
                    text: "取消"
                    onClicked: {
                        quitDialog.pendingCloseAction = null
                        quitDialog.close()
                    }
                }
                Button {
                    text: "退出"
                    highlighted: true
                    onClicked: {
                        quitDialog.close()
                        if (quitDialog.pendingCloseAction) {
                            navigation.requestGuardedAction("关闭窗口", quitDialog.pendingCloseAction)
                            quitDialog.pendingCloseAction = null
                        }
                    }
                }
            }
        }
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
            window.showNotice(kind, text)
        }
        function onTelemetryConsentRequiredChanged() {
            if (window.appCtrl && window.appCtrl.telemetryConsentRequired) {
                telemetryDialog.open()
            }
        }
    }

    Connections {
        target: window.runCtrl
        function onScriptAutoWarningRequested(text) {
            window.showNotice("error", text)
        }
    }

    Component.onCompleted: {
        if (window.appCtrl && window.appCtrl.telemetryConsentRequired) {
            telemetryDialog.open()
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
