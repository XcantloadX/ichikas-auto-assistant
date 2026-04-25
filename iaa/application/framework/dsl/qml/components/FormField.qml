import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: root
    property var labelText: null
    property alias control: controlLoader.sourceComponent
    readonly property bool hasLabel: labelText !== null && labelText !== undefined

    Label {
        visible: root.hasLabel
        text: root.hasLabel ? String(root.labelText) : ""
        Layout.preferredWidth: root.hasLabel ? 120 : 0
        Layout.alignment: Qt.AlignVCenter
    }

    Loader {
        id: controlLoader
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignVCenter
    }
}
