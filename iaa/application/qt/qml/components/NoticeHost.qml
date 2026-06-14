/**
 * Toast 通知的视觉宿主。
 *
 * 在 ApplicationWindow 中放置一个实例即可；渲染层通过 `parent: Overlay.overlay`
 * 悬浮于所有内容之上，不占用布局空间。
 * 组件挂载时自动向 Notice 单例注册，卸载时注销。
 *
 * 不要直接调用 show()，始终通过单例 `App.Notice.show()` 触发通知。
 */
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".." as App

Item {
    id: root
    visible: false

    /** Toast 自动消失的时长（毫秒） */
    readonly property int _duration: 4000
    /** 同时可见的 Toast 上限，超出时移除最旧的一条 */
    readonly property int _maxCount: 5

    /**
     * 追加一条 Toast 通知。由 Notice 单例调用，不应直接使用。
     * 超出 _maxCount 时移除队列头部最旧的一条。
     * @param {string} kind - 通知类型：`"info"` | `"success"` | `"warning"` | `"error"`
     * @param {string} text - 通知正文
     */
    function show(kind, text) {
        if (toastModel.count >= root._maxCount) {
            toastModel.remove(0)
        }
        toastModel.append({ kind: kind, text: text })
    }

    ListModel {
        id: toastModel
    }

    ListView {
        parent: Overlay.overlay
        anchors.right: parent.right
        anchors.rightMargin: 24
        anchors.top: parent.top
        anchors.topMargin: 24
        width: 340
        height: contentHeight
        spacing: 8
        model: toastModel
        interactive: false

        add: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic }
            NumberAnimation { property: "x"; from: 32; to: 0; duration: 220; easing.type: Easing.OutCubic }
        }
        remove: Transition {
            NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 160; easing.type: Easing.InCubic }
            NumberAnimation { property: "x"; from: 0; to: 32; duration: 160; easing.type: Easing.InCubic }
        }
        displaced: Transition {
            NumberAnimation { properties: "x,y"; duration: 200; easing.type: Easing.OutCubic }
        }

        delegate: Item {
            id: toastItem

            required property int index
            required property string kind
            required property string text

            width: 340
            height: toastCard.implicitHeight

            readonly property color accentColor: {
                if (App.IaaTheme.isDark) {
                    switch (toastItem.kind) {
                        case "success": return "#6ccb5f"
                        case "warning": return "#fce100"
                        case "error":   return "#ff99a4"
                        default:        return "#60cdff"
                    }
                } else {
                    switch (toastItem.kind) {
                        case "success": return "#107c10"
                        case "warning": return "#c05a00"
                        case "error":   return "#c42b1c"
                        default:        return "#0067c0"
                    }
                }
            }
            readonly property color iconColor: accentColor
            readonly property string icon: {
                switch (toastItem.kind) {
                    case "success": return "\uF298"   // ic_fluent_checkmark_circle_20_regular
                    case "warning": return "\uF869"   // ic_fluent_warning_20_regular
                    case "error":   return "\uF3F1"   // ic_fluent_error_circle_20_regular
                    default:        return "\uF4A3"   // ic_fluent_info_20_regular
                }
            }

            Timer {
                interval: root._duration
                running: true
                onTriggered: toastModel.remove(toastItem.index)
            }

            Rectangle {
                id: toastCard
                width: parent.width
                implicitHeight: contentRow.implicitHeight + 20
                radius: 6
                color: App.IaaTheme.isDark ? "#2d2d2d" : "#ffffff"
                border.color: App.IaaTheme.isDark ? Qt.rgba(1,1,1,0.12) : Qt.rgba(0,0,0,0.12)
                border.width: 1

                // Accent bar — inset 1px to stay inside the border
                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.margins: 1
                    width: 3
                    radius: 2
                    color: toastItem.accentColor
                }

                RowLayout {
                    id: contentRow
                    anchors.left: parent.left
                    anchors.leftMargin: 14
                    anchors.right: parent.right
                    anchors.rightMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8

                    Label {
                        text: toastItem.icon
                        color: toastItem.iconColor
                        font.family: "FluentSystemIcons-Regular"
                        font.pixelSize: 16
                        Layout.alignment: Qt.AlignVCenter
                    }

                    Label {
                        Layout.fillWidth: true
                        text: toastItem.text
                        color: App.IaaTheme.fg
                        wrapMode: Text.Wrap
                        font.pixelSize: 13
                        lineHeightMode: Text.ProportionalHeight
                        lineHeight: 1.3
                    }

                    Item {
                        Layout.preferredWidth: 24
                        Layout.preferredHeight: 24
                        Layout.alignment: Qt.AlignVCenter

                        Rectangle {
                            anchors.fill: parent
                            radius: 4
                            color: closeMouse.containsMouse ? App.IaaTheme.hover : "transparent"
                        }

                        Label {
                            anchors.centerIn: parent
                            text: "\uF369"   // ic_fluent_dismiss_20_regular
                            font.family: "FluentSystemIcons-Regular"
                            font.pixelSize: 12
                            color: closeMouse.containsMouse
                                ? App.IaaTheme.fg
                                : (App.IaaTheme.isDark ? Qt.rgba(1,1,1,0.45) : Qt.rgba(0,0,0,0.45))
                        }

                        MouseArea {
                            id: closeMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: toastModel.remove(toastItem.index)
                        }
                    }
                }
            }
        }
    }

    Component.onCompleted: App.Notice.registerHost(root)
    Component.onDestruction: App.Notice.registerHost(null)
}
