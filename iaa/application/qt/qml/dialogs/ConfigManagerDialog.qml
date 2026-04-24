import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: root
    modal: true
    title: "配置管理"
    width: 400
    padding: 16
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    anchors.centerIn: Overlay.overlay

    property var configNames: []

    function reload() {
        var profiles = JSON.parse(settingsController.optionsJson()).profiles || [];
        configNames = profiles;
    }

    Component.onCompleted: reload()

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
                    if (settingsController.createProfile(newConfigName.text.trim())) {
                        newConfigName.text = "";
                        root.reload();
                        sideNav.reloadConfigs();
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
                        settingsController.renameProfile(renameDialog.targetConfigName, renameDialog.newName.trim());
                        renameDialog.close();
                        root.reload();
                        sideNav.reloadConfigs();
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
                        settingsController.deleteProfile(deleteConfirmDialog.targetConfigName);
                        deleteConfirmDialog.close();
                        root.reload();
                        sideNav.reloadConfigs();
                    }
                }
            }
        }
    }
}