pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../components"
import "../../../../qt/qml" as App

ColumnLayout {
    id: root

    required property var field
    required property var formController

    spacing: 4

    function indexOfId(items, value) {
        if (!items) {
            return -1
        }
        for (let i = 0; i < items.length; ++i) {
            let item = items[i]
            if (item && item.id === value) {
                return i
            }
        }
        return -1
    }

    FormField {
        Layout.fillWidth: true
        labelText: root.field.label
        helpText: root.field.helpText || ""
        errorText: root.field.error || ""

        RowLayout {
            Select {
                Layout.fillWidth: true
                enabled: !!root.field.enabled
                model: root.field.options || []
                textRole: "label"
                valueRole: "id"
                currentIndex: root.indexOfId(root.field.options || [], root.field.value)
                onActivated: root.formController.setValue(root.field.id, currentValue)
            }
            Button {
                visible: !!(root.field.props && root.field.props.refreshable)
                text: root.field.loading ? App.Globals.t("settings.action.loading") : App.Globals.t("settings.action.refresh")
                enabled: !!root.field.enabled
                onClicked: root.formController.triggerAction(root.field.id, "refresh", "{}")
            }
        }
    }

}
