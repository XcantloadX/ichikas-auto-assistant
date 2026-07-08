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

    function indexOfValue(items, value) {
        if (!items) {
            return -1
        }
        for (let i = 0; i < items.length; ++i) {
            let item = items[i]
            if (item && item.value === value) {
                return i
            }
        }
        return -1
    }

    FormField {
        Layout.fillWidth: true
        labelText: root.field.label
        helpText: root.field.helpText || ""
        errorText: root.field.error || ""

        RowLayout {
            Select {
                Layout.fillWidth: true
                enabled: !!root.field.enabled && !(root.field.props && root.field.props.loading)
                model: (root.field.props && root.field.props.loading) ? [{label: "载入中...", value: ""}] : (root.field.options || [])
                textRole: "label"
                valueRole: "value"
                currentIndex: (root.field.props && root.field.props.loading) ? 0 : root.indexOfValue(root.field.options || [], root.field.value)
                onActivated: root.formController.setValue(root.field.id, currentValue)
            }
            BusyIndicator {
                visible: !!(root.field.props && root.field.props.loading)
                running: !!(root.field.props && root.field.props.loading)
                Layout.preferredWidth: 20
                Layout.preferredHeight: 20
            }
            Button {
                text: (root.field.props && root.field.props.loading) ? "获取中..." : "刷新"
                enabled: !!root.field.enabled && !(root.field.props && root.field.props.loading)
                onClicked: root.formController.triggerAction(root.field.id, "refresh", "{}")
            }
        }
    }

}
