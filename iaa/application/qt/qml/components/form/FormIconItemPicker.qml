pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../controls"
import "../"
import "formUtils.js" as F

// 图标网格选择器（表单版），复刻自原 DSL DslIconItemPicker + GridItemPicker。
// 用于需要从带分组、带图标选项中选择一个值的场景。
ColumnLayout {
    id: root
    Layout.fillWidth: true
    property string label: ""
    property string help: ""
    property var options: []
    property var value: null
    property var binder: null
    property string field: ""
    property int cellSize: 68
    property int iconSize: 44
    property int columns: 0
    property int popupMaxHeight: 0
    property bool showLabel: true
    property int popupPadding: 8
    property int cellRadius: 8
    // 底层值存储为单元素列表（如 tasks.challenge_live.characters）时为 true
    property bool singleToArray: false

    signal userSelected(var v)

    readonly property var _eb: F.effectiveBinder(binder, parent)

    readonly property var _val: {
        var _ = _eb ? _eb.data : null   // 强制建立对 _eb.data 的绑定依赖
        return (_eb && field) ? _eb.get(field, null) : value
    }

    FieldRegistrar {
        id: _registrar
        startParent: root.parent
        binder: root._eb
        field: root.field
        label: root.label
        prefixRevision: root._eb ? (root._eb.prefix.length) : 0
    }
    Connections {
        target: root._eb
        enabled: !!root._eb && !!root.field && !!root.label
        function onPrefixChanged() { _registrar.prefixRevision++ }
    }

    function _normalizeOption(item, category) {
        if (item && typeof item === "object") {
            let label = item.label !== undefined && item.label !== null ? String(item.label) : ""
            let value = item.value !== undefined ? item.value : item
            let image = item.image !== undefined && item.image !== null ? item.image
                : (item.icon !== undefined && item.icon !== null ? item.icon
                    : (item.img !== undefined && item.img !== null ? item.img : ""))
            let group = item.category !== undefined && item.category !== null
                ? String(item.category)
                : (item.group !== undefined && item.group !== null ? String(item.group)
                    : (category || ""))
            return {
                label: label,
                value: value,
                image: image ? String(image) : "",
                category: group,
            }
        }
        let text = String(item)
        return { label: text, value: item, image: "", category: category || "" }
    }

    function _flattenOptions(options) {
        let flat = []
        if (!Array.isArray(options)) {
            return flat
        }
        if (options.length > 0 && options[0] && typeof options[0] === "object" && Array.isArray(options[0].options)) {
            for (let i = 0; i < options.length; ++i) {
                let group = options[i]
                let title = group.group || group.title || group.label || ""
                let items = Array.isArray(group.options) ? group.options : []
                for (let j = 0; j < items.length; ++j) {
                    flat.push(_normalizeOption(items[j], title))
                }
            }
            return flat
        }
        for (let i = 0; i < options.length; ++i) {
            flat.push(_normalizeOption(options[i], ""))
        }
        return flat
    }

    function _selectedValue() {
        let v = root._val
        if (Array.isArray(v) && v.length > 0) {
            return v[0]
        }
        return v
    }

    function _indexOfValue(items, value) {
        if (!items) {
            return -1
        }
        for (let i = 0; i < items.length; ++i) {
            if (String(items[i].value) === String(value)) {
                return i
            }
        }
        return -1
    }

    property var normalizedOptions: _flattenOptions(root.options)

    FormField {
        Layout.fillWidth: true
        labelText: root.label
        helpText: root.help

        GridItemPicker {
            id: picker
            Layout.fillWidth: true
            enabled: root.enabled
            model: root.normalizedOptions
            textRole: "label"
            valueRole: "value"
            imageRole: "image"
            categoryRole: "category"
            columns: root.columns
            cellSize: root.cellSize
            iconSize: root.iconSize
            popupMaxHeight: root.popupMaxHeight
            showLabel: root.showLabel
            popupPadding: root.popupPadding
            cellRadius: root.cellRadius
            currentIndex: root._indexOfValue(root.normalizedOptions, root._selectedValue())

            onActivated: function(index) {
                let options = root.normalizedOptions
                if (index < 0 || index >= options.length) {
                    return
                }
                let selected = options[index]
                let out = root.singleToArray ? [selected.value] : selected.value
                if (root._eb && root.field) root._eb.set(root.field, out)
                else root.userSelected(out)
            }
        }
    }

    FormError {
        Layout.leftMargin: 4
        info: root._eb ? root._eb.error(root.field) : null
    }
}
