pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../../../framework/dsl/qml/components"
import "../../../framework/dsl/qml/controls"

ColumnLayout {
    id: root

    // 由 FieldRenderer.customLoader 在 onLoaded 设初始值，onFieldChanged 同步后续更新
    property var field: null
    property var formController: null
    readonly property var fieldProps: field && field.props ? field.props : ({})
    readonly property string resetText: fieldProps.resetText || "恢复分辨率"

    spacing: 4

    property var normalizedOptions: {
        let options = (root.field && root.field.options) ? root.field.options : []
        let mapped = []
        for (let i = 0; i < options.length; ++i) {
            let item = options[i]
            if (item && typeof item === "object") {
                mapped.push({
                    label: (item.label !== undefined && item.label !== null) ? String(item.label) : String(item.value || ""),
                    value: item.value
                })
            } else {
                mapped.push({ label: String(item), value: item })
            }
        }
        return mapped
    }

    function indexOfValue(items, value) {
        if (!items) return -1
        for (let i = 0; i < items.length; ++i) {
            let v = (items[i] && typeof items[i] === "object") ? items[i].value : items[i]
            if (v === value) return i
        }
        return -1
    }

    // field 变化时（初始注入或后续更新）用 callLater 确保 model 先更新再设 currentIndex
    onFieldChanged: Qt.callLater(function() {
        combo.currentIndex = root.indexOfValue(root.normalizedOptions, root.field ? root.field.value : null)
    })

    FormField {
        Layout.fillWidth: true
        labelText: root.field ? root.field.label : ""
        helpText: (root.field && root.field.helpText) ? root.field.helpText : ""
        errorText: (root.field && root.field.error) ? root.field.error : ""

        RowLayout {
            Select {
                id: combo
                Layout.fillWidth: true
                enabled: !!(root.field && root.field.enabled)
                model: root.normalizedOptions
                textRole: "label"
                valueRole: "value"

                onActivated: function(index) {
                    if (!root.field || !root.formController) return
                    let options = root.normalizedOptions
                    if (index < 0 || index >= options.length) return
                    let item = options[index]
                    let value = (item && typeof item === "object") ? item.value : item
                    root.formController.setValue(root.field.id, value)
                }
            }

            Button {
                text: root.resetText
                enabled: !!(root.field && root.field.enabled)
                onClicked: {
                    if (root.field && root.formController)
                        root.formController.triggerAction(root.field.id, "reset", "{}")
                }
            }
        }
    }
}
