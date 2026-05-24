pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../../../framework/dsl/qml/components"

ColumnLayout {
    // 由 FieldRenderer.customLoader 在 onLoaded 设初始值，onFieldChanged 同步后续更新
    property var field: null
    property var formController: null

    spacing: 4

    property var normalizedOptions: {
        let options = (field && field.options) ? field.options : []
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
        combo.currentIndex = indexOfValue(normalizedOptions, field ? field.value : null)
    })

    FormField {
        Layout.fillWidth: true
        labelText: field ? field.label : ""
        helpText: (field && field.helpText) ? field.helpText : ""
        errorText: (field && field.error) ? field.error : ""

        RowLayout {
            ComboBox {
                id: combo
                Layout.fillWidth: true
                enabled: !!(field && field.enabled)
                model: normalizedOptions
                textRole: "label"
                valueRole: "value"

                onActivated: function(index) {
                    if (!field || !formController) return
                    let options = normalizedOptions
                    if (index < 0 || index >= options.length) return
                    let item = options[index]
                    let value = (item && typeof item === "object") ? item.value : item
                    formController.setValue(field.id, value)
                }
            }

            Button {
                text: "恢复分辨率"
                enabled: !!(field && field.enabled)
                onClicked: {
                    if (field && formController)
                        formController.triggerAction(field.id, "reset", "{}")
                }
            }
        }
    }
}
