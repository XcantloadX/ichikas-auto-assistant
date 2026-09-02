import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../controls"
import "../"
import "formUtils.js" as F

// 分辨率设置：下拉选择 + 「恢复分辨率」按钮。
ColumnLayout {
    id: root
    Layout.fillWidth: true
    property string label: ""
    property string help: ""
    property var options: []
    property var value: null
    property var binder: null
    property string field: ""
    property bool resetEnabled: true

    signal resetRequested()

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

    function _findIndex() {
        var val = root._val
        var items = root.options || []
        for (var i = 0; i < items.length; ++i) {
            var it = items[i]
            var v = (it && typeof it === "object") ? it.value : it
            if (v === val) return i
        }
        return -1
    }

    FormField {
        Layout.fillWidth: true
        labelText: root.label
        helpText: root.help

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            Select {
                Layout.fillWidth: true
                enabled: root.enabled
                model: root.options
                textRole: "label"
                valueRole: "value"
                currentIndex: root._findIndex()
                onActivated: function(index, value) {
                    var v = root.options && index >= 0 && index < root.options.length
                        ? (typeof root.options[index] === "object" ? root.options[index].value : root.options[index])
                        : value
                    if (root._eb && root.field) root._eb.set(root.field, v)
                }
            }

            Button {
                text: "恢复分辨率"
                enabled: root.resetEnabled && root.enabled
                onClicked: root.resetRequested()
            }
        }
    }

    FormError {
        Layout.leftMargin: 4
        info: root._eb ? root._eb.error(root.field) : null
    }
}
