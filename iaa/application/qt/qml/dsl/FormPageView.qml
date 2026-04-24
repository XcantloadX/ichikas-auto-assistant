pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../components"
import "."

ScrollView {
    id: root
    property var runtime: ({"groups": []})
    property var formController

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

                Layout.fillWidth: true
                title: modelData.title || ""

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    Repeater {
                        model: groupDelegate.modelData.fields || []
                        delegate: Item {
                            id: fieldDelegate
                            required property var modelData

                            Layout.fillWidth: true
                            implicitWidth: renderer.implicitWidth
                            implicitHeight: renderer.implicitHeight

                            FieldRenderer {
                                id: renderer
                                anchors.left: parent.left
                                anchors.right: parent.right
                                field: fieldDelegate.modelData
                                formController: root.formController
                            }
                        }
                    }
                }
            }
        }
    }
}
