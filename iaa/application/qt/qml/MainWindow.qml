import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "pages"
import "dialogs"

import "components"

ApplicationWindow {
    id: window
    width: 980
    height: 680
    visible: true
    title: appController.windowTitle
    font.family: "Microsoft YaHei UI"
    color: "transparent"
    background: null

    property string noticeKind: "info"
    property string noticeText: ""

    function showNotice(kind, text) {
        noticeKind = kind
        noticeText = text
        noticePopup.open()
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        SideNavigationBar {
            id: sideNav
            Layout.fillHeight: true
            model: ["控制", "配置", "关于"]
            currentConfig: settingsController.stateJson() ? JSON.parse(settingsController.stateJson()).profileName || "default" : "default"

            onCurrentChanging: function(index, previousIndex) {
                var previousPage = stack.children[previousIndex]
                if (previousPage && typeof previousPage.hasUnsavedChanges === "function" && previousPage.hasUnsavedChanges()) {
                    confirmSwitchDialog.targetIndex = index
                    confirmSwitchDialog.previousIndex = previousIndex
                    confirmSwitchDialog.open()
                } else {
                    sideNav.confirmSwitch(index)
                }
            }

            onConfigSwitchRequested: function(name) {
                if (settingsController.switchProfile(name)) {
                    sideNav.currentConfig = name;
                }
            }

            onOpenConfigManager: {
                configManagerDialog.open()
            }
        }

        Connections {
            target: settingsController
            function onConfigSwitched() {
                sideNav.reloadConfigs();
                sideNav.currentConfig = settingsController.stateJson() ? JSON.parse(settingsController.stateJson()).profileName || "default" : "default";
            }
        }

        StackLayout {
            id: stack
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: sideNav.currentIndex

            ControlPage {
                id: controlPage
                autoLiveDialog: autoLiveDialog
                onShowNotice: function(kind, text) { window.showNotice(kind, text) }
            }

            SettingsPage {
                id: settingsPage
                onShowNotice: function(kind, text) { window.showNotice(kind, text) }
            }

            AboutPage {}
        }
    }

    AutoLiveDialog {
        id: autoLiveDialog
        onShowNotice: function(kind, text) { window.showNotice(kind, text) }
    }

    ConfigManagerDialog {
        id: configManagerDialog
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
                        appController.setTelemetryConsent(false)
                        telemetryDialog.close()
                    }
                }
                Button {
                    text: "允许"
                    highlighted: true
                    onClicked: {
                        appController.setTelemetryConsent(true)
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
                Button { text: "取消"; onClicked: quitDialog.close() }
                Button {
                    text: "退出"
                    highlighted: true
                    onClicked: {
                        quitDialog.close()
                        appController.confirmClose()
                        Qt.quit()
                    }
                }
            }
        }
    }

    Dialog {
        id: confirmSwitchDialog
        modal: true
        title: "未保存更改"
        standardButtons: Dialog.NoButton
        width: 420
        anchors.centerIn: Overlay.overlay

        property int targetIndex: 0
        property int previousIndex: 0

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: "当前页面有未保存的更改，请选择操作："
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: 8
                Button {
                    text: "返回"
                    onClicked: {
                        confirmSwitchDialog.close()
                    }
                }
                Button {
                    text: "丢弃更改"
                    onClicked: {
                        var previousPage = stack.children[confirmSwitchDialog.previousIndex]
                        if (previousPage && typeof previousPage.discardChanges === "function") {
                            previousPage.discardChanges()
                        }
                        confirmSwitchDialog.close()
                        sideNav.confirmSwitch(confirmSwitchDialog.targetIndex)
                    }
                }
                Button {
                    text: "保存更改"
                    highlighted: true
                    onClicked: {
                        var previousPage = stack.children[confirmSwitchDialog.previousIndex]
                        if (previousPage && typeof previousPage.saveChanges === "function") {
                            previousPage.saveChanges()
                        }
                        confirmSwitchDialog.close()
                        sideNav.confirmSwitch(confirmSwitchDialog.targetIndex)
                    }
                }
            }
        }
    }

    Connections {
        target: appController
        function onNotificationRaised(kind, text) {
            window.showNotice(kind, text)
        }
        function onTelemetryConsentRequiredChanged() {
            if (appController.telemetryConsentRequired) {
                telemetryDialog.open()
            }
        }
    }

    Connections {
        target: runController
        function onScriptAutoWarningRequested(text) {
            window.showNotice("error", text)
        }
    }

    Component.onCompleted: {
        if (appController.telemetryConsentRequired) {
            telemetryDialog.open()
        }
    }

    onClosing: function(close) {
        if (runController.running) {
            close.accepted = false
            quitDialog.open()
        } else {
            close.accepted = appController.confirmClose()
        }
    }
}
