pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../components"

ColumnLayout {
    id: root

    required property var field
    required property var formController

    spacing: 4

    FormField {
        Layout.fillWidth: true
        labelText: root.field.label
        helpText: root.field.helpText || ""
        TextField {
            Layout.fillWidth: true
            text: String(root.field.value || "")
            enabled: !!root.field.enabled
            placeholderText: root.field.props && root.field.props.placeholder ? root.field.props.placeholder : ""
            onTextEdited: root.formController.setValue(root.field.id, text)
        }
    }

    Label {
        visible: !!root.field.error
        text: root.field.error || ""
        color: "#DC3545"
    }
}
