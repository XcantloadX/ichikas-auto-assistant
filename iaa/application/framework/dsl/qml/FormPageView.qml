pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "components"
import "."

ScrollView {
    id: root
    property var runtime: ({"groups": [], "fieldMap": {}})
    property var formController
    property var extraKinds: ({})

    anchors.fill: parent
    clip: true
    contentWidth: availableWidth

    ColumnLayout {
        width: root.availableWidth
        spacing: 16

        Repeater {
            model: root.runtime.groups || []
            delegate: GroupBox {
                id: groupDelegate
                required property var modelData
                required property int index

                property bool groupVisible: modelData.visible !== false

                Connections {
                    target: root.formController
                    function onGroupUpdated(idx, visible) {
                        if (idx === groupDelegate.index) {
                            groupDelegate.groupVisible = visible
                        }
                    }
                }

                Layout.fillWidth: true
                visible: groupDelegate.groupVisible
                title: modelData.title || ""

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    Repeater {
                        model: groupDelegate.modelData.fieldIds || []
                        delegate: Item {
                            id: fieldDelegate
                            required property string modelData

                            Layout.fillWidth: true
                            visible: renderer.fieldVisible
                            implicitWidth: renderer.implicitWidth
                            implicitHeight: renderer.implicitHeight

                            FieldRenderer {
                                id: renderer
                                anchors.left: parent.left
                                anchors.right: parent.right
                                fieldId: fieldDelegate.modelData
                                initialField: root.runtime.fieldMap[fieldDelegate.modelData] || {}
                                formController: root.formController
                                extraKinds: root.extraKinds
                            }
                        }
                    }
                }
            }
        }
    }
}
