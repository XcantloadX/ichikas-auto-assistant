import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: root
    property alias labelText: label.text
    property string helpText: ""
    property alias control: controlLoader.sourceComponent
    readonly property bool hasLabel: labelText !== null && labelText !== undefined

    RowLayout {
        Layout.preferredWidth: 120
        Layout.alignment: Qt.AlignVCenter
        spacing: 6

        Label {
            id: label
            Layout.alignment: Qt.AlignVCenter
        }

        HelpTip {
            visible: root.helpText.length > 0
            richText: root.helpText
            Layout.alignment: Qt.AlignVCenter
        }
    }

    Loader {
        id: controlLoader
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignVCenter
    }
}
