import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".." as App
import IaaApp 1.0

// 主窗口 tab 栏：应用图标、总览 tab、config tab 列表、+ 新建、☰ 配置管理、⚙ 偏好。
// currentIndex: 0 = 总览，1 = config tab（由内部点击驱动，TitleBar 读取）
Item {
    id: root

    required property var configManagerDialog

    property int currentIndex: 0
    property var tabs: []

    signal settingsRequested()

    // 供 TitleBar 同步给 Win32 hit-test：tab 按钮区右边界
    readonly property real interactiveEnd: interactiveRow.width + 4

    clip: true

    Row {
        id: interactiveRow
        anchors.left: parent.left
        anchors.leftMargin: 4
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        spacing: 0

        // ── 应用图标 ───────────────────────────────────────────────────
        Item {
            width: 48
            height: parent.height

            Image {
                anchors.centerIn: parent
                width: 16; height: 16
                source: App.Globals.assetPath("icon_round.png")
                fillMode: Image.PreserveAspectFit
                smooth: true
                visible: status === Image.Ready
            }
        }

        // ── Tab 列表 ───────────────────────────────────────────────────
        Row {
            id: tabRow
            height: parent.height
            spacing: 2

            // ── 总览 Tab（固定，不可关闭）──────────────────────────────
            Item {
                id: overviewTab
                width: Math.min(240, Math.max(120, overviewLabel.implicitWidth + 24))
                height: parent.height

                HoverHandler { id: overviewHover }

                MouseArea {
                    anchors.fill: parent
                    onClicked: root.currentIndex = 0
                    onPressed: event => event.accepted = true
                }

                Item {
                    anchors.fill: parent
                    clip: true
                    visible: root.currentIndex === 0

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: parent.height + radius
                        radius: 6
                        color: palette.window
                    }
                }

                Rectangle {
                    anchors.fill: parent
                    anchors.leftMargin: 2
                    anchors.rightMargin: 2
                    visible: root.currentIndex !== 0 && overviewHover.hovered
                    radius: 5
                    color: Qt.rgba(palette.windowText.r, palette.windowText.g, palette.windowText.b, 0.08)
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 6

                    Label {
                        id: overviewLabel
                        Layout.fillWidth: true
                        text: "总览"
                        elide: Text.ElideRight
                        font.pixelSize: 13
                        font.weight: root.currentIndex === 0 ? Font.Medium : Font.Normal
                        opacity: root.currentIndex === 0 ? 1.0 : 0.75
                    }
                }
            }

            // ── Config Tab 列表（动态，可关闭）────────────────────────
            Repeater {
                model: root.tabs
                delegate: Item {
                    id: tabDelegate

                    // modelData 在 Repeater model 刷新过渡期间可能为 undefined
                    readonly property bool _isActive: modelData ? (!!modelData.isActive && root.currentIndex === 1) : false
                    readonly property string _name: modelData ? (modelData.configName ?? "") : ""

                    width: Math.min(240, Math.max(120, tabLabel.implicitWidth + 48))
                    height: parent.height

                    HoverHandler { id: tabHover }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (modelData) {
                                root.currentIndex = 1
                                if (!modelData.isActive)
                                    TabManager.setActiveTab(modelData.index)
                            }
                        }
                        onPressed: event => event.accepted = true
                    }

                    // 激活态：仅顶部圆角的卡片（与内容区无缝衔接）
                    Item {
                        anchors.fill: parent
                        clip: true
                        visible: tabDelegate._isActive

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            height: parent.height + radius
                            radius: 6
                            color: palette.window
                        }
                    }

                    // 非激活态：hover 时显示圆角背景
                    Rectangle {
                        anchors.fill: parent
                        anchors.leftMargin: 2
                        anchors.rightMargin: 2
                        visible: !tabDelegate._isActive && tabHover.hovered
                        radius: 5
                        color: Qt.rgba(palette.windowText.r, palette.windowText.g, palette.windowText.b, 0.08)
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 6
                        spacing: 4

                        Label {
                            id: tabLabel
                            Layout.fillWidth: true
                            text: tabDelegate._name
                            elide: Text.ElideRight
                            font.pixelSize: 13
                            font.weight: tabDelegate._isActive ? Font.Medium : Font.Normal
                            opacity: tabDelegate._isActive ? 1.0 : 0.75
                        }

                        // × 关闭按钮（FluentSystemIcons dismiss_20 = ）
                        Rectangle {
                            Layout.preferredWidth: 20
                            Layout.preferredHeight: 20
                            Layout.alignment: Qt.AlignVCenter
                            radius: 4
                            color: tabCloseMouseArea.containsMouse
                                ? Qt.rgba(palette.windowText.r, palette.windowText.g, palette.windowText.b, 0.15)
                                : "transparent"

                            Text {
                                anchors.centerIn: parent
                                font.family: "FluentSystemIcons-Regular"
                                font.pixelSize: 9
                                text: "\uF369"   // ChromeClose
                                color: palette.windowText
                                opacity: tabDelegate._isActive ? 0.9 : 0.6
                            }

                            MouseArea {
                                id: tabCloseMouseArea
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    if (modelData) TabManager.requestCloseTab(modelData.index)
                                }
                            }
                        }
                    }
                }
            }
        }

        // ── + 新建 Tab（FluentSystemIcons add_20 = ）──────────────
        Item {
            width: 32
            height: parent.height

            HoverHandler { id: addBtnHover }

            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 4; anchors.bottomMargin: 4
                anchors.leftMargin: 2; anchors.rightMargin: 2
                radius: 5
                color: addBtnHover.hovered
                    ? Qt.rgba(palette.windowText.r, palette.windowText.g, palette.windowText.b, 0.08)
                    : "transparent"
            }

            Text {
                anchors.centerIn: parent
                font.family: "FluentSystemIcons-Regular"
                font.pixelSize: 13
                text: "\uF109"   // Add
                color: palette.windowText
                opacity: 0.7
            }

            MouseArea {
                anchors.fill: parent
                onClicked: addTabPopup.open()
                onPressed: event => event.accepted = true
            }

            Popup {
                id: addTabPopup
                y: parent.height
                width: 200
                padding: 4
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                property var available: []
                onAboutToShow: {
                    available = JSON.parse(TabManager.availableConfigsJson())
                }

                contentItem: Column {
                    width: addTabPopup.availableWidth
                    spacing: 0

                    Repeater {
                        model: addTabPopup.available
                        delegate: ItemDelegate {
                            width: parent.width
                            text: modelData
                            onClicked: {
                                TabManager.openTab(modelData)
                                addTabPopup.close()
                            }
                        }
                    }

                    ItemDelegate {
                        width: parent.width
                        text: "所有配置均已打开"
                        enabled: false
                        visible: addTabPopup.available.length === 0
                    }
                }
            }
        }

        // ── ☰ 配置管理（FluentSystemIcons navigation_20 = ）────
        Item {
            width: configMgrRow.implicitWidth + 16
            height: parent.height

            HoverHandler { id: configMgrBtnHover }

            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 4; anchors.bottomMargin: 4
                anchors.leftMargin: 2; anchors.rightMargin: 2
                radius: 5
                color: configMgrBtnHover.hovered
                    ? Qt.rgba(palette.windowText.r, palette.windowText.g, palette.windowText.b, 0.08)
                    : "transparent"
            }

            Row {
                id: configMgrRow
                anchors.centerIn: parent
                spacing: 4

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    font.family: "FluentSystemIcons-Regular"
                    font.pixelSize: 14
                    text: "\uF560"   // GlobalNavButton
                    color: palette.windowText
                    opacity: 0.7
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "配置"
                    font.pixelSize: 13
                    color: palette.windowText
                    opacity: 0.7
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: root.configManagerDialog.open()
                onPressed: event => event.accepted = true
            }
        }

        // ── ⚙ 偏好（FluentSystemIcons settings_20 = ）────────────
        Item {
            width: settingsRow.implicitWidth + 16
            height: parent.height

            HoverHandler { id: settingsBtnHover }

            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 4; anchors.bottomMargin: 4
                anchors.leftMargin: 2; anchors.rightMargin: 2
                radius: 5
                color: settingsBtnHover.hovered
                    ? Qt.rgba(palette.windowText.r, palette.windowText.g, palette.windowText.b, 0.08)
                    : "transparent"
            }

            Row {
                id: settingsRow
                anchors.centerIn: parent
                spacing: 4

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    font.family: "FluentSystemIcons-Regular"
                    font.pixelSize: 14
                    text: "\uF6A9"   // Settings
                    color: palette.windowText
                    opacity: 0.7
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "偏好"
                    font.pixelSize: 13
                    color: palette.windowText
                    opacity: 0.7
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: root.settingsRequested()
                onPressed: event => event.accepted = true
            }
        }
    }
}
