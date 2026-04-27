import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Control {
    id: root
    background: null
    property string title: "NewPage"
    property bool showTitle: true
    default property alias contentData: contentArea.data
    /** 紧挨着标题文本右侧的内容 */
    property alias titleRightContent: titleRightArea.data
    /** 标题栏最右侧的操作按钮 */
    property alias headerActions: headerActionsArea.data

    // topPadding: 20
    padding: 20

    contentItem: ColumnLayout {
        id: column
        spacing: 20

        RowLayout {
            visible: root.showTitle

            Label {
                text: root.title
                font.pixelSize: 30
                // font.weight: Font.Light
            }

            Item {
                id: titleRightArea
                visible: children.length > 0
                implicitWidth: childrenRect.width
                implicitHeight: childrenRect.height
            }

            Item { Layout.fillWidth: true }

            Item {
                id: headerActionsArea
                visible: children.length > 0
                implicitWidth: childrenRect.width
                implicitHeight: childrenRect.height
            }
        }

        Item {
            id: contentArea
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}