pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../../components"

ColumnLayout {
    id: root

    required property var field
    required property var formController
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
        RowLayout {
            ComboBox {
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
                    if (root.field.props && root.field.props.singleFromList) {
                        root.formController.setValue(root.field.id, [root.itemValue(selected)])
                    } else {
                        root.formController.setValue(root.field.id, root.itemValue(selected))
                    }
                }

                contentItem: Text {
                    leftPadding: 6
                    rightPadding: combo.indicator.width + combo.spacing
                    text: {
                        if (!combo.model || combo.currentIndex < 0 || combo.currentIndex >= combo.model.length) {
                            return ""
                        }
                        return root.itemLabel(combo.model[combo.currentIndex])
                    }
                    font: combo.font
                    color: combo.enabled ? combo.palette.text : combo.palette.placeholderText
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }
            }

            Button {
                visible: !!(root.field.props && root.field.props.withResetButton)
                text: "恢复分辨率"
                enabled: !!root.field.enabled
                onClicked: root.formController.triggerAction(root.field.id, "resetResolution", "{}")
            }
        }
    }

    Label {
        visible: !!root.field.error
        text: root.field.error || ""
        color: "#DC3545"
    }
}
