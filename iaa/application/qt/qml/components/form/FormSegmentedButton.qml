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

        SegmentedButton {
            Layout.fillWidth: true
            model: root.options
            textRole: "label"
            valueRole: "value"
            value: root._val
            onActivated: function(index, value) {
                if (root._eb && root.field) root._eb.set(root.field, value)
                else root.userSelected(value)
            }
        }
    }

    FormError {
        Layout.leftMargin: 126
        info: root._eb ? root._eb.error(root.field) : null
    }
}
