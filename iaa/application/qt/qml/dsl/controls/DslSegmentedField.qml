pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../../components"

ColumnLayout {
    id: root

    required property var field
    required property var formController

    spacing: 4

    function indexOfValue(items, value) {
        if (!items) {
            return -1
        }
        for (let i = 0; i < items.length; ++i) {
            let item = items[i]
            let current = (item && typeof item === "object") ? item.value : item
            if (current === value) {
                return i
            }
        }
        return -1
    }

    FormField {
        Layout.fillWidth: true
        labelText: root.field.label
        SegmentedButton {
            Layout.fillWidth: true
            enabled: !!root.field.enabled
            model: root.field.options || []
            textRole: "label"
            valueRole: "value"
            currentIndex: root.indexOfValue(root.field.options || [], root.field.value)
            onActivated: function(index, value) {
                root.formController.setValue(root.field.id, value)
            }
        }
    }

    Label {
        visible: !!root.field.error
        text: root.field.error || ""
        color: "#DC3545"
    }
}
