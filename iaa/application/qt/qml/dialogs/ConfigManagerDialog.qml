import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".." as App

Dialog {
    id: root
    modal: true
    title: "配置管理"
    width: 400
    padding: 16
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    anchors.centerIn: Overlay.overlay

    property var configNames: []
    required property var navigation
    required property var settingsCtrl

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
                placeholderText: "新配置名称"
            }

            Button {
                text: "新建"
                highlighted: true
                enabled: newConfigName.text.trim().length > 0
                onClicked: {
                    var name = newConfigName.text.trim()
                    if (name.length > 0) {
                        root.navigation.requestGuardedAction("切换到新配置", function() {
                            root.settingsCtrl.createProfile(name)
                        })
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
            model: root.configNames

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
                text: "关闭"
                onClicked: root.close()
            }
        }
    }

    Dialog {
        id: renameDialog
        modal: true
        title: "重命名配置"
        width: 360
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: Overlay.overlay

        property string targetConfigName: ""
        property string newName: ""

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                text: "请输入新名称:"
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
                    text: "取消"
                    onClicked: renameDialog.close()
                }
                Button {
                    text: "确定"
                    highlighted: true
                    enabled: renameDialog.newName.trim().length > 0
                    onClicked: {
                        var oldName = renameDialog.targetConfigName
                        var newName = renameDialog.newName.trim()
                        var isCurrent = oldName === App.ProfileStore.currentProfileName
                        var runner = function() {
                            root.settingsCtrl.renameProfile(oldName, newName)
                        }
                        if (isCurrent) {
                            root.navigation.requestGuardedAction("重命名当前配置", runner)
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
        title: "确认删除"
        width: 360
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: Overlay.overlay

        property string targetConfigName: ""

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: "确定要删除配置 '" + deleteConfirmDialog.targetConfigName + "' 吗？此操作不可撤销。"
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button {
                    text: "取消"
                    onClicked: deleteConfirmDialog.close()
                }
                Button {
                    text: "删除"
                    highlighted: true
                    onClicked: {
                        var name = deleteConfirmDialog.targetConfigName
                        var isCurrent = name === App.ProfileStore.currentProfileName
                        var runner = function() {
                            root.settingsCtrl.deleteProfile(name)
                        }
                        if (isCurrent) {
                            root.navigation.requestGuardedAction("删除当前配置", runner)
                        } else {
                            runner()
                        }
                        deleteConfirmDialog.close()
                    }
                }
            }
        }
    }
}
