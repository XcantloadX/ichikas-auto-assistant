import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// 表单字段校验提示文本：error 用红色，warning 用橙色。不占布局空间。
// 用法：info 传入 {severity, message} 或 null；为 null 时不可见且不占布局空间。
Item {
    id: root
    Layout.fillWidth: true
    property var info: null

    readonly property bool _has: !!info && !!info.message
    visible: _has
    implicitHeight: _has ? label.implicitHeight + 2 : 0

    Label {
        id: label
        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter }
        text: root._has ? root.info.message : ""
        color: (root._has && root.info.severity === "warning") ? "#D29922" : "#DC3545"
        wrapMode: Text.Wrap
        visible: root._has
    }
}
