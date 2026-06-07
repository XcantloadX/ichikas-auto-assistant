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
        errorText: root.field.error || ""
        SegmentedButton {
            Layout.fillWidth: true
            enabled: !!root.field.enabled
            model: root.field.options || []
            textRole: "label"
            valueRole: "value"
            value: root.field.value
            onActivated: function(index, value) {
                root.formController.setValue(root.field.id, value)
            }
        }
    }

}
