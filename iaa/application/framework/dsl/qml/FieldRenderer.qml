pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "./controls"

Item {
    id: root

    required property string fieldId
    required property var initialField
    required property var formController

    // 外部注入的自定义 kind 映射：kind 字符串 → QML 文件 URL
    // 例如：{ "resolution_select": Qt.resolvedUrl("../controls/DslResolutionSelect.qml") }
    property var extraKinds: ({})

    // 工作副本：初始化时从 initialField 同步，后续由 fieldUpdated 信号更新。
    // 不使用绑定，避免因 runtimeChanged 全量刷新时被重置而打断用户输入。
    property var field: root.initialField
    readonly property bool fieldVisible: root.field.visible !== false
    readonly property bool isCustomKind: root.field.kind in root.extraKinds

    onInitialFieldChanged: root.field = root.initialField

    Connections {
        target: root.formController
        function onFieldUpdated(id, fieldJson) {
            if (id === root.fieldId) {
                root.field = JSON.parse(fieldJson)
            }
        }
    }

    implicitWidth: root.isCustomKind ? customLoader.implicitWidth : builtinLoader.implicitWidth
    implicitHeight: root.isCustomKind ? customLoader.implicitHeight : builtinLoader.implicitHeight

    // 内置 kind：通过 sourceComponent 创建，field/formController 在 Component 内绑定
    Loader {
        id: builtinLoader
        active: root.fieldVisible && !root.isCustomKind
        anchors.left: parent.left
        anchors.right: parent.right

        sourceComponent: {
            switch (root.field.kind) {
            case "text": return textFieldComponent
            case "select": return selectFieldComponent
            case "segmented": return segmentedFieldComponent
            case "checkbox": return checkboxFieldComponent
            case "transfer_list": return transferListComponent
            case "hotkey": return hotkeyFieldComponent
            case "notice_block": return noticeBlockComponent
            case "icon_item_picker": return iconItemPickerComponent
            default: return unsupportedComponent
            }
        }
    }

    // 自定义 kind：通过 source URL 加载，field/formController 在 onLoaded 中设初始值，
    // 后续更新由 onFieldChanged 驱动（避免 Qt.binding 与 ComboBox 内部赋值冲突）
    Loader {
        id: customLoader
        active: root.fieldVisible && root.isCustomKind
        anchors.left: parent.left
        anchors.right: parent.right
        source: root.isCustomKind ? root.extraKinds[root.field.kind] : ""

        onLoaded: {
            if (item) {
                item.field = root.field
                item.formController = root.formController
            }
        }
    }

    onFieldChanged: {
        if (root.isCustomKind && customLoader.item) {
            customLoader.item.field = root.field
        }
    }

    Component {
        id: textFieldComponent
        DslTextField {
            field: root.field
            formController: root.formController
        }
    }

    Component {
        id: selectFieldComponent
        DslSelectField {
            field: root.field
            formController: root.formController
        }
    }

    Component {
        id: segmentedFieldComponent
        DslSegmentedField {
            field: root.field
            formController: root.formController
        }
    }

    Component {
        id: checkboxFieldComponent
        DslCheckboxField {
            field: root.field
            formController: root.formController
        }
    }

    Component {
        id: transferListComponent
        DslTransferList {
            field: root.field
            formController: root.formController
        }
    }

    Component {
        id: hotkeyFieldComponent
        DslHotkeyField {
            field: root.field
            formController: root.formController
        }
    }

    Component {
        id: noticeBlockComponent
        DslNoticeBlock {
            field: root.field
            formController: root.formController
        }
    }

    Component {
        id: iconItemPickerComponent
        DslIconItemPicker {
            field: root.field
            formController: root.formController
        }
    }

    Component {
        id: unsupportedComponent
        Label {
            color: "#DC3545"
            text: "不支持的字段类型: " + (root.field.kind || "")
        }
    }
}
