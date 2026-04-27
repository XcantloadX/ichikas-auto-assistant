pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../components"

ColumnLayout {
    id: root

    required property var field
    required property var formController

    property int availableIndex: -1
    property int selectedIndex: -1
    property var normalizedOptions: {
        let options = root.field.options || []
        let mapped = []
        for (let i = 0; i < options.length; ++i) {
            let item = options[i]
            if (item && typeof item === "object") {
                mapped.push({
                    value: item.value,
                    label: (item.label !== undefined && item.label !== null) ? String(item.label) : String(item.value || "")
                })
            } else {
                let text = String(item)
                mapped.push({ value: item, label: text })
            }
        }
        return mapped
    }

    spacing: 4

    function toArray(value) {
        if (Array.isArray(value)) {
            return value
        }
        if (value === undefined || value === null) {
            return []
        }
        if (typeof value.length === "number") {
            let out = []
            for (let i = 0; i < value.length; ++i) {
                out.push(value[i])
            }
            return out
        }
        return []
    }

    function selectedValues() {
        let rawValues = toArray(field.value)
        let values = []
        for (let i = 0; i < rawValues.length; ++i) {
            let item = rawValues[i]
            values.push((item && typeof item === "object") ? item.value : item)
        }
        return values
    }

    function allOptions() {
        return Array.isArray(root.normalizedOptions) ? root.normalizedOptions : []
    }

    function selectedItems() {
        let values = selectedValues()
        let options = allOptions()
        let out = []
        for (let i = 0; i < values.length; ++i) {
            let value = values[i]
            let found = null
            for (let j = 0; j < options.length; ++j) {
                if (options[j].value === value) {
                    found = options[j]
                    break
                }
            }
            out.push(found || { value: value, label: value })
        }
        return out
    }

    function availableItems() {
        let values = selectedValues()
        let options = allOptions()
        return options.filter(function(item) {
            return values.indexOf(item.value) < 0
        })
    }

    function commit(values) {
        formController.setValue(field.id, values)
    }

    function moveToSelected() {
        var available = availableItems()
        if (availableIndex < 0 || availableIndex >= available.length) {
            return
        }
        var selected = selectedValues()
        selected.push(available[availableIndex].value)
        availableIndex = -1
        commit(selected)
    }

    function moveToAvailable() {
        var selected = selectedValues()
        if (selectedIndex < 0 || selectedIndex >= selected.length) {
            return
        }
        selected.splice(selectedIndex, 1)
        selectedIndex = -1
        commit(selected)
    }

    function moveUp() {
        var selected = selectedValues()
        if (selectedIndex <= 0 || selectedIndex >= selected.length) {
            return
        }
        var item = selected[selectedIndex]
        selected.splice(selectedIndex, 1)
        selected.splice(selectedIndex - 1, 0, item)
        selectedIndex -= 1
        commit(selected)
    }

    function moveDown() {
        var selected = selectedValues()
        if (selectedIndex < 0 || selectedIndex >= selected.length - 1) {
            return
        }
        var item = selected[selectedIndex]
        selected.splice(selectedIndex, 1)
        selected.splice(selectedIndex + 1, 0, item)
        selectedIndex += 1
        commit(selected)
    }

    FormField {
        Layout.fillWidth: true
        labelText: root.field.label
        helpText: root.field.helpText || ""

        RowLayout {
            spacing: 10

            ListView {
                id: selectedList
                Layout.fillWidth: true
                Layout.preferredHeight: root.field.props && root.field.props.height ? root.field.props.height : 220
                model: root.selectedItems()
                clip: true
                delegate: ItemDelegate {
                    required property int index
                    required property var modelData
                    width: ListView.view.width
                    highlighted: index === root.selectedIndex
                    text: {
                        if (typeof modelData !== "undefined" && modelData && typeof modelData === "object") {
                            return String(modelData.label || modelData.value || "")
                        }
                        return String(modelData || "")
                    }
                    onClicked: root.selectedIndex = index
                }
            }

            ColumnLayout {
                Button {
                    text: "← 添加"
                    enabled: !!root.field.enabled
                    onClicked: root.moveToSelected()
                }
                Button {
                    text: "移除 →"
                    enabled: !!root.field.enabled
                    onClicked: root.moveToAvailable()
                }
                Button {
                    text: "上移"
                    enabled: !!root.field.enabled && !!(root.field.props && root.field.props.reorderable)
                    onClicked: root.moveUp()
                }
                Button {
                    text: "下移"
                    enabled: !!root.field.enabled && !!(root.field.props && root.field.props.reorderable)
                    onClicked: root.moveDown()
                }
            }

            ListView {
                id: availableList
                Layout.fillWidth: true
                Layout.preferredHeight: root.field.props && root.field.props.height ? root.field.props.height : 220
                model: root.availableItems()
                clip: true
                delegate: ItemDelegate {
                    required property int index
                    required property var modelData
                    width: ListView.view.width
                    highlighted: index === root.availableIndex
                    text: {
                        if (typeof modelData !== "undefined" && modelData && typeof modelData === "object") {
                            return String(modelData.label || modelData.value || "")
                        }
                        return String(modelData || "")
                    }
                    onClicked: root.availableIndex = index
                }
            }
        }
    }

    Label {
        visible: !!root.field.error
        text: root.field.error || ""
        color: "#DC3545"
    }
}
