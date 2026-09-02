import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".." as App

Dialog {
    id: root
    modal: true
    title: App.Globals.t("config_manager.title")
    width: 400
    padding: 16
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    anchors.centerIn: Overlay.overlay

    property var configNames: []
    required property var navigation
    required property var settingsCtrl
    required property var tabManager

    function reload() {
        root.configNames = JSON.parse(App.ProfileStore.profilesJson).profiles || []
    }

    Component.onCompleted: reload()

    Connections {
        target: App.ProfileStore

        function onProfilesChanged() {
            root.reload()
        }
    }

    contentItem: ColumnLayout {
        spacing: 12

        RowLayout {
            Layout.fillWidth: true

            TextField {
                id: newConfigName
                Layout.fillWidth: true
                placeholderText: App.Globals.t("config_manager.new_placeholder")
            }

            Button {
                text: App.Globals.t("common.create")
                highlighted: true
                enabled: newConfigName.text.trim().length > 0
                onClicked: {
                    var name = newConfigName.text.trim()
                    if (name.length > 0) {
<<<<<<< HEAD
                        let doCreate = function () { root.tabManager.createProfile(name); }
                        root.navigation.requestGuardedAction("切换到新配置", doCreate)
=======
                        root.navigation.requestGuardedAction(App.Globals.t("guard.switch_new_config"), function() {
                            root.settingsCtrl.createProfile(name)
                        })
>>>>>>> feat/en-server
                        newConfigName.text = ""
                    }
                }
            }
        }

        ListView {
            id: configList
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 200
            clip: true
            model: root.configNames

            ScrollBar.vertical: ScrollBar {
                policy: configList.contentHeight > configList.height
                        ? ScrollBar.AlwaysOn
                        : ScrollBar.AlwaysOff
            }

            delegate: RowLayout {
                width: ListView.view.width
                height: 40

                ItemDelegate {
                    Layout.fillWidth: true
                    height: parent.height
                    text: modelData.label
                }

                Button {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    text: "✎"
                    font.pixelSize: 16
                    onClicked: {
                        renameDialog.targetConfigName = modelData.value;
                        renameDialog.newName = modelData.label;
                        renameDialog.open();
                    }
                }

                Button {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    text: "×"
                    font.pixelSize: 18
                    enabled: root.configNames.length > 1
                    visible: root.configNames.length > 1
                    onClicked: {
                        deleteConfirmDialog.targetConfigName = modelData.value;
                        deleteConfirmDialog.open();
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignRight

            Button {
                text: App.Globals.t("common.close")
                onClicked: root.close()
            }
        }
    }

    Dialog {
        id: renameDialog
        modal: true
        title: App.Globals.t("config_manager.rename_title")
        width: 360
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: Overlay.overlay

        property string targetConfigName: ""
        property string newName: ""

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                text: App.Globals.t("config_manager.rename_prompt")
            }
            TextField {
                id: renameInput
                Layout.fillWidth: true
                text: renameDialog.newName
                onTextChanged: renameDialog.newName = text
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button {
                    text: App.Globals.t("common.cancel")
                    onClicked: renameDialog.close()
                }
                Button {
                    text: App.Globals.t("common.ok")
                    highlighted: true
                    enabled: renameDialog.newName.trim().length > 0 && root.settingsCtrl !== null
                    onClicked: {
                        var oldName = renameDialog.targetConfigName
                        var newName = renameDialog.newName.trim()
                        var isCurrent = root.tabManager.isTabOpen(oldName)
                        var runner = function() {
                            root.settingsCtrl.renameProfile(oldName, newName)
                        }
                        if (isCurrent) {
                            root.navigation.requestGuardedAction(App.Globals.t("guard.rename_current_config"), runner)
                        } else {
                            runner()
                        }
                        renameDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: deleteConfirmDialog
        modal: true
        title: App.Globals.t("config_manager.delete_title")
        width: 360
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: Overlay.overlay

        property string targetConfigName: ""

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: App.Globals.t("config_manager.delete_prompt").replace("{name}", deleteConfirmDialog.targetConfigName)
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button {
                    text: App.Globals.t("common.cancel")
                    onClicked: deleteConfirmDialog.close()
                }
                Button {
                    text: App.Globals.t("common.delete")
                    highlighted: true
                    onClicked: {
                        var name = deleteConfirmDialog.targetConfigName
                        if (root.settingsCtrl === null) {
                            deleteConfirmDialog.close()
                            return
                        }
<<<<<<< HEAD
                        // 如果该配置的 tab 正在运行，拒绝删除
                        if (!root.tabManager.closeTabForConfig(name)) {
                            deleteConfirmDialog.close()
                            return
=======
                        if (isCurrent) {
                            root.navigation.requestGuardedAction(App.Globals.t("guard.delete_current_config"), runner)
                        } else {
                            runner()
>>>>>>> feat/en-server
                        }
                        root.settingsCtrl.deleteProfile(name)
                        deleteConfirmDialog.close()
                    }
                }
            }
        }
    }
}
