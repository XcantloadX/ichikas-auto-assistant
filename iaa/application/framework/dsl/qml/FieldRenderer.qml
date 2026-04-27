pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "./controls"

Item {
    id: root

    required property var field
    required property var formController

    implicitWidth: loader.implicitWidth
    implicitHeight: loader.implicitHeight

    Loader {
        id: loader
        anchors.left: parent.left
        anchors.right: parent.right

        sourceComponent: {
            switch (root.field.kind) {
            case "text": return textFieldComponent
            case "select": return selectFieldComponent
            case "segmented": return segmentedFieldComponent
            case "checkbox": return checkboxFieldComponent
            case "mumu_picker": return mumuPickerComponent
            case "transfer_list": return transferListComponent
            default: return unsupportedComponent
            }
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
        id: mumuPickerComponent
        DslMumuPicker {
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
        id: unsupportedComponent
        Label {
            color: "#DC3545"
            text: "不支持的字段类型: " + (root.field.kind || "")
        }
    }
}
