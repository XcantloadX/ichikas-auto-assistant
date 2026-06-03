import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

PageContainer {
    id: root
    showTitle: false
    padding: 0

    property var _tabs: []

    function _reload() {
        if (typeof tabManager !== 'undefined' && tabManager)
            _tabs = JSON.parse(tabManager.tabsJson())
    }

    Component.onCompleted: _reload()

    Connections {
        target: typeof tabManager !== 'undefined' ? tabManager : null
        function onTabsChanged() { root._reload() }
        function onActiveTabChanged() { root._reload() }
    }

    ScrollView {
        id: scrollView
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        Flow {
            width: scrollView.availableWidth
            topPadding: 32
            leftPadding: 32
            rightPadding: 32
            bottomPadding: 32
            spacing: 16

            Repeater {
                model: root._tabs

                delegate: Rectangle {
                    id: card

                    readonly property var runCtrl: tabManager.runControllerAt(modelData.index)
                    readonly property var progBridge: tabManager.progressBridgeAt(modelData.index)

                    width: 260
                    height: contentCol.implicitHeight + 32
                    radius: 8
                    color: cardHover.containsMouse
                        ? Qt.rgba(palette.windowText.r, palette.windowText.g, palette.windowText.b, 0.06)
                        : Qt.rgba(palette.windowText.r, palette.windowText.g, palette.windowText.b, 0.03)
                    border.color: Qt.rgba(palette.windowText.r, palette.windowText.g, palette.windowText.b, 0.1)
                    border.width: 1

                    HoverHandler { id: cardHover }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: window.navigateTo("tab", modelData.index)
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
                                color: (card.runCtrl && card.runCtrl.running)
                                    ? palette.highlight
                                    : Qt.rgba(palette.windowText.r, palette.windowText.g, palette.windowText.b, 0.3)
                            }

                            Label {
                                text: {
                                    if (!card.runCtrl) return "就绪"
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
}
