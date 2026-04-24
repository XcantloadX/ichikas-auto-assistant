import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".." as App

// import Iaa.Controllers 1.0

Rectangle {
    id: root
    width: 200
    color: "transparent"

    property var model: []
    property int currentIndex: 0
    property int previousIndex: 0
    property var configNames: []
    property string currentConfig: "default"
    signal currentChanging(int index, int previousIndex)
    signal configSwitchRequested(string name)
    signal openConfigManager()

    function confirmSwitch(index) {
        root.currentIndex = index
    }

    function reloadConfigs() {
        configNames = JSON.parse(settingsController.optionsJson()).profiles || [];
    }

    Component.onCompleted: {
        reloadConfigs();
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: 6
        anchors.bottomMargin: 12
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        spacing: 12

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 82
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                // anchors.margins: 12
                spacing: 10

                Rectangle {
                    Layout.preferredWidth: 66
                    Layout.preferredHeight: 66
                    radius: 22
                    color: "transparent"
                    clip: true

                    Image {
                        anchors.fill: parent
                        anchors.margins: 2
                        source: App.Globals.assetPath("chibi/chr_il_1.png")
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Label {
                        Layout.fillWidth: true
                        text: "一歌小助手"
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                        color: "#202020"
                        verticalAlignment: Text.AlignVCenter
                    }

                    Label {
                        Layout.fillWidth: true
                        text: "版本 v" + appController.version
                        font.pixelSize: 12
                        color: "#202020"
                        verticalAlignment: Text.AlignVCenter
                    }
                }

            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            ComboBox {
                Layout.fillWidth: true
                model: root.configNames
                textRole: "label"
                valueRole: "value"
                currentIndex: {
                    for (var i = 0; i < model.length; i++) {
                        if (model[i].value === root.currentConfig) return i;
                    }
                    return 0;
                }
                enabled: !runController.running && !runController.isStarting && !runController.isStopping
                onActivated: {
                    var selected = currentValue;
                    if (selected && selected !== root.currentConfig) {
                        root.configSwitchRequested(selected);
                    }
                }
            }

            Button {
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                text: "⚙"
                font.pixelSize: 16
                enabled: !runController.running && !runController.isStarting && !runController.isStopping
                onClicked: root.openConfigManager()
            }
        }

        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.model
            spacing: 4
            interactive: false

            delegate: ItemDelegate {
                id: delegate
                width: listView.width
                height: 40
                text: modelData
                font.pixelSize: 14
                highlighted: root.currentIndex === index

                onClicked: {
                    root.previousIndex = root.currentIndex
                    root.currentChanging(index, root.previousIndex)
                }
            }
        }
    }
}
