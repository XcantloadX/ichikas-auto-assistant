pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../components"

ColumnLayout {
    id: root

    required property var field
    required property var formController
    readonly property var fieldProps: root.field.props || ({})
    readonly property string refreshText: root.fieldProps.refreshText || "刷新"
    readonly property string loadingText: root.fieldProps.loadingText || "获取中..."
    property var normalizedOptions: {
        let options = root.field.options || []
        let mapped = []
        for (let i = 0; i < options.length; ++i) {
            let item = options[i]
            if (item && typeof item === "object") {
                mapped.push({
                    label: (item.label !== undefined && item.label !== null) ? String(item.label) : String(item.value || ""),
                    value: item.value
                })
            } else {
                let text = String(item)
                mapped.push({ label: text, value: item })
            }
        }
        return mapped
    }

    spacing: 4

    function itemValue(item) {
        return (item && typeof item === "object") ? item.value : item
    }

    function itemLabel(item) {
        return (item && typeof item === "object") ? (item.label || item.value || "") : String(item)
    }

    function indexOfValue(items, value) {
        if (!items) {
            return -1
        }
        for (let i = 0; i < items.length; ++i) {
            if (root.itemValue(items[i]) === value) {
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
                id: combo
                Layout.fillWidth: true
                enabled: !!root.field.enabled
                model: root.normalizedOptions
                textRole: "label"
                valueRole: "value"
                currentIndex: root.indexOfValue(root.normalizedOptions, root.field.value)

                onActivated: function(index) {
                    let options = root.normalizedOptions
                    if (index < 0 || index >= options.length) {
                        return
                    }
                    let selected = options[index]
                    root.formController.setValue(root.field.id, root.itemValue(selected))
                }
            }

            Button {
                visible: !!root.field.refreshable
                text: root.field.loading ? root.loadingText : root.refreshText
                enabled: !!root.field.enabled
                onClicked: root.formController.triggerAction(root.field.id, "refresh", "{}")
            }
        }
    }

}
