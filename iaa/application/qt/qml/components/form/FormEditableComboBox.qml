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
    signal userEdited(string text)

    readonly property var _eb: F.effectiveBinder(binder, parent)

    readonly property var _val: {
        var _ = _eb ? _eb.data : null
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

    property bool _suppressEditText: false

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

        ComboBox {
            id: combo
            Layout.fillWidth: true
            model: root.options
            textRole: "label"
            editable: true
            currentIndex: -1
            onActivated: function(index) {
                var v = root.options && index >= 0 && index < root.options.length
                    ? (typeof root.options[index] === "object" ? root.options[index].value : root.options[index])
                    : ""
                root.userSelected(v)
                root.userEdited(v)
            }
            onEditTextChanged: {
                if (!root._suppressEditText) {
                    root.userEdited(editText)
                }
            }
            Component.onCompleted: {
                var idx = root._findIndex()
                if (idx >= 0) {
                    currentIndex = idx
                } else if (root._val) {
                    editText = String(root._val)
                }
            }
        }
    }

    Connections {
        target: root
        function on_ValChanged() {
            var idx = root._findIndex()
            root._suppressEditText = true
            if (idx >= 0) {
                combo.currentIndex = idx
            } else {
                combo.editText = String(root._val ?? "")
            }
            root._suppressEditText = false
        }
    }

    FormError {
        Layout.leftMargin: 126
        info: root._eb ? root._eb.error(root.field) : null
    }
}
