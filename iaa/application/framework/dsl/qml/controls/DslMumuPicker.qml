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

    function indexOfId(items, value) {
        if (!items) {
            return -1
        }
        for (let i = 0; i < items.length; ++i) {
            let item = items[i]
            if (item && item.id === value) {
                return i
            }
        }
        return -1
    }

    FormField {
        Layout.fillWidth: true
        labelText: root.field.label
        helpText: root.field.helpText || ""

        RowLayout {
            ComboBox {
                Layout.fillWidth: true
                enabled: !!root.field.enabled
                model: root.field.options || []
                textRole: "label"
                valueRole: "id"
                currentIndex: root.indexOfId(root.field.options || [], root.field.value)
                onActivated: root.formController.setValue(root.field.id, currentValue)
            }
            Button {
                visible: !!(root.field.props && root.field.props.refreshable)
                text: root.field.loading ? "获取中..." : "刷新"
                enabled: !!root.field.enabled
                onClicked: root.formController.triggerAction(root.field.id, "refresh", "{}")
            }
        }
    }

    Label {
        visible: !!root.field.error
        text: root.field.error || ""
        color: "#DC3545"
    }
}
