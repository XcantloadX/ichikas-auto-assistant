import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import ".." as App
import IaaApp 1.0

PageContainer {
    id: root
    showTitle: false
    padding: 0

    required property var configManagerDialog

    property var _allConfigs: []

    function _reload() {
        _allConfigs = JSON.parse(TabManager.allConfigsJson())
    }

    Component.onCompleted: _reload()

    Connections {
        target: TabManager
        function onTabsChanged() { root._reload() }
        function onActiveTabChanged() { root._reload() }
    }

    ScrollView {
        id: scrollView
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: scrollView.availableWidth
            spacing: 0

            // ── Brand（居中）────────────────────────────────────────────────
            RowLayout {
                Layout.topMargin: 48
                Layout.alignment: Qt.AlignHCenter
                spacing: 14

                Rectangle {
                    width: 100
                    height: 100
                    color: "transparent"
                    clip: true

                    Image {
                        anchors.fill: parent
                        source: App.Globals.assetPath("chibi/ichika.png")
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }
                }

                ColumnLayout {
                    spacing: 2

                    Label {
                        text: {
                            var h = new Date().getHours()
                            if (h < 6)  return "晚上好！"
                            if (h < 11) return "早上好！"
                            if (h < 13) return "中午好！"
                            if (h < 18) return "下午好！"
                            return "晚上好！"
                        }
                        font.pixelSize: 30
                        font.weight: Font.DemiBold
                    }

                    Label {
                        text: "一歌小助手 v" + AppController.version
                        font.pixelSize: 16
                        opacity: 0.65
                    }
                }
            }

            // ── 有配置 ────────────────────────────────────────────────────────
            ColumnLayout {
                visible: root._allConfigs.length > 0
                Layout.fillWidth: true
                spacing: 0

                // 启动按钮行（居中）
                RowLayout {
                    Layout.topMargin: 28
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 12

                    Button {
                        id: seqBtn
                        readonly property bool isStopMode: TabManager.batchMode === "sequential"
                        highlighted: true
                        enabled: TabManager.batchMode === ""
                                 || (isStopMode && !TabManager.stopAllBusy)
                        leftPadding: 16
                        rightPadding: 16
                        topPadding: 8
                        bottomPadding: 8
                        onClicked: {
                            if (isStopMode) TabManager.stopAll()
                            else TabManager.startAllSequential()
                        }

                        contentItem: Row {
                            spacing: 7
                            anchors.centerIn: parent

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                font.family: "FluentSystemIcons-Regular"
                                font.pixelSize: 17
                                text: seqBtn.isStopMode ? "\uF72A" : "\uF605"
                                color: seqBtn.highlighted ? (App.IaaTheme.isDark ? "black" : "white") : App.IaaTheme.fg
                            }

                            Label {
                                anchors.verticalCenter: parent.verticalCenter
                                text: {
                                    if (!seqBtn.isStopMode)    return "连续启动"
                                    if (TabManager.stopAllBusy) return "停止中"
                                    return "停止所有"
                                }
                                font.pixelSize: 14
                                color: seqBtn.highlighted ? (App.IaaTheme.isDark ? "black" : "white") : App.IaaTheme.fg
                            }
                        }
                    }

                    Button {
                        id: parBtn
                        readonly property bool isStopMode: TabManager.batchMode === "parallel"
                        highlighted: true
                        enabled: TabManager.batchMode === ""
                                 || (isStopMode && !TabManager.stopAllBusy)
                        leftPadding: 16
                        rightPadding: 16
                        topPadding: 8
                        bottomPadding: 8
                        onClicked: {
                            if (isStopMode) TabManager.stopAll()
                            else TabManager.startAllParallel()
                        }

                        contentItem: Row {
                            spacing: 7
                            anchors.centerIn: parent

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                font.family: "FluentSystemIcons-Regular"
                                font.pixelSize: 17
                                text: parBtn.isStopMode ? "\uF72A" : "\uF100"
                                color: parBtn.highlighted ? (App.IaaTheme.isDark ? "black" : "white") : App.IaaTheme.fg
                            }

                            Label {
                                anchors.verticalCenter: parent.verticalCenter
                                text: {
                                    if (!parBtn.isStopMode)    return "并行启动"
                                    if (TabManager.stopAllBusy) return "停止中"
                                    return "停止所有"
                                }
                                font.pixelSize: 14
                                color: parBtn.highlighted ? (App.IaaTheme.isDark ? "black" : "white") : App.IaaTheme.fg
                            }
                        }
                    }
                }

                // 配置小标题
                Label {
                    Layout.topMargin: 28
                    Layout.leftMargin: 40
                    text: "配置"
                    font.pixelSize: 13
                    font.weight: Font.Medium
                    opacity: 0.55
                }

                // 配置卡片列表（全部配置）
                Flow {
                    Layout.fillWidth: true
                    Layout.topMargin: 10
                    Layout.leftMargin: 32
                    Layout.rightMargin: 32
                    Layout.bottomMargin: 32
                    spacing: 16

                    Repeater {
                        model: root._allConfigs

                        delegate: Rectangle {
                            id: card

                            readonly property int _tabIdx: modelData.tabIndex
                            readonly property var runCtrl: _tabIdx >= 0 ? TabManager.runControllerAt(_tabIdx) : null
                            readonly property var progBridge: _tabIdx >= 0 ? TabManager.progressBridgeAt(_tabIdx) : null

                            width: 260
                            height: contentCol.implicitHeight + 32
                            radius: 8
                            color: cardHover.containsMouse
                                ? (App.IaaTheme.isDark ? Qt.rgba(1,1,1,0.06) : Qt.rgba(0,0,0,0.06))
                                : (App.IaaTheme.isDark ? Qt.rgba(1,1,1,0.03) : Qt.rgba(0,0,0,0.03))
                            border.color: App.IaaTheme.isDark ? Qt.rgba(1,1,1,0.1) : Qt.rgba(0,0,0,0.1)
                            border.width: 1

                            HoverHandler { id: cardHover }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (card._tabIdx < 0) {
                                        TabManager.openTab(modelData.configName)
                                    } else {
                                        TabManager.setActiveTab(card._tabIdx)
                                        window.navigateTo("tab", TabManager.activeTabIndex)
                                    }
                                }
                            }

                            ColumnLayout {
                                id: contentCol
                                anchors {
                                    left: parent.left
                                    right: parent.right
                                    top: parent.top
                                    margins: 16
                                }
                                spacing: 8

                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.configName
                                    font.pixelSize: 15
                                    font.weight: Font.Medium
                                    elide: Text.ElideRight
                                }

                                RowLayout {
                                    spacing: 6

                                    Rectangle {
                                        width: 8
                                        height: 8
                                        radius: 4
                                        color: {
                                            if (card.runCtrl && card.runCtrl.running) return palette.highlight
                                            if (card.runCtrl && card.runCtrl.isQueued) return "#f59e0b"
                                            return App.IaaTheme.isDark ? Qt.rgba(1,1,1,0.3) : Qt.rgba(0,0,0,0.3)
                                        }
                                    }

                                    Label {
                                        text: {
                                            if (!card.runCtrl) return "就绪"
                                            if (card.runCtrl.isQueued) return "排队中"
                                            if (card.runCtrl.isStarting) return "启动中"
                                            if (card.runCtrl.isStopping) return "停止中"
                                            if (card.runCtrl.running) return "运行中"
                                            return "就绪"
                                        }
                                        font.pixelSize: 12
                                        opacity: 0.7
                                    }

                                    Label {
                                        Layout.fillWidth: true
                                        text: (card.runCtrl && card.runCtrl.running && card.runCtrl.currentTaskName)
                                            ? "· " + card.runCtrl.currentTaskName
                                            : ""
                                        font.pixelSize: 12
                                        opacity: 0.5
                                        elide: Text.ElideRight
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: visible ? -1 : 0
                                    Layout.minimumHeight: 0
                                    clip: true
                                    spacing: 4
                                    visible: card.runCtrl && card.runCtrl.running

                                    ProgressBar {
                                        Layout.fillWidth: true
                                        value: card.progBridge ? (card.progBridge.progressPercent / 100.0) : 0
                                    }

                                    Label {
                                        Layout.fillWidth: true
                                        text: card.progBridge ? card.progBridge.statusText : ""
                                        font.pixelSize: 11
                                        opacity: 0.55
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // ── 无配置 ────────────────────────────────────────────────────────
            ColumnLayout {
                visible: root._allConfigs.length === 0
                Layout.fillWidth: true
                Layout.topMargin: 32
                Layout.leftMargin: 40
                Layout.bottomMargin: 32
                spacing: 12

                Label {
                    text: "你还没有创建任何配置"
                    font.pixelSize: 14
                    opacity: 0.7
                }

                Row {
                    spacing: 5

                    Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "点击"
                        font.pixelSize: 14
                        opacity: 0.7
                    }

                    Button {
                        id: createBtn
                        highlighted: true
                        text: "创建配置"
                        font.pixelSize: 14
                        topPadding: 4
                        bottomPadding: 4
                        leftPadding: 10
                        rightPadding: 10
                        anchors.verticalCenter: parent.verticalCenter
                        onClicked: root.configManagerDialog.open()
                    }

                    Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "或顶部标签栏的"
                        font.pixelSize: 14
                        opacity: 0.7
                    }

                    Rectangle {
                        width: 22
                        height: 22
                        radius: 4
                        color: App.IaaTheme.hover
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            font.family: "FluentSystemIcons-Regular"
                            font.pixelSize: 13
                            text: ""
                            color: App.IaaTheme.fg
                            opacity: 0.7
                        }
                    }

                    Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "号创建新配置"
                        font.pixelSize: 14
                        opacity: 0.7
                    }
                }
            }
        }
    }
}
