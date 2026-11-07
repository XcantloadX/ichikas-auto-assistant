import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../controls"
import "../"
import "formUtils.js" as F

ColumnLayout {
    id: root
    Layout.fillWidth: true
    property string label: ""
    property string help: ""
    property var options: []
    property var value: null
    property var binder: null
    property string field: ""

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

    RowLayout {
        RowLayout {
            Layout.preferredWidth: 120
            spacing: 6

            Label { text: root.label; Layout.alignment: Qt.AlignVCenter }

            HelpTip {
                visible: root.help.length > 0
                richText: root.help
                Layout.alignment: Qt.AlignVCenter
            }
        }

        Select {
            Layout.fillWidth: true
            model: root.options
            textRole: "label"
            valueRole: "value"
            currentIndex: root._findIndex()
            onActivated: function(index, value) {
                var v = root.options && index >= 0 && index < root.options.length
                    ? (typeof root.options[index] === "object" ? root.options[index].value : root.options[index])
                    : value
                if (root._eb && root.field) root._eb.set(root.field, v)
                else root.userSelected(v)
            }
        }
    }

    FormError {
        Layout.leftMargin: 126
        info: root._eb ? root._eb.error(root.field) : null
    }
}
