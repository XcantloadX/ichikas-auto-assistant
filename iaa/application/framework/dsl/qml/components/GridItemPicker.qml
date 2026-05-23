pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../../../../qt/qml" as App

ComboBox {
    id: control

    property string imageRole: "image"
    property string categoryRole: "category"
    property int columns: 0
    property int cellSize: 68
    property int iconSize: 44
    property int popupMaxHeight: 0
    property bool showLabel: true
    property int cellRadius: 8
    property int popupPadding: 8

    function _modelCount() {
        if (!control.model) {
            return 0
        }
        if (typeof control.model.count === "number") {
            return control.model.count
        }
        if (typeof control.model.length === "number") {
            return control.model.length
        }
        return 0
    }

    function _modelItemAt(index) {
        if (!control.model) {
            return null
        }
        if (typeof control.model.get === "function") {
            return control.model.get(index)
        }
        return control.model[index]
    }

    function _itemLabel(item) {
        if (!item || typeof item !== "object") {
            return ""
        }
        let label = item[control.textRole]
        if (label === undefined || label === null) {
            return ""
        }
        return String(label)
    }

    function _itemImage(item) {
        if (!item || typeof item !== "object") {
            return ""
        }
        let image = item[control.imageRole]
        if (image === undefined || image === null) {
            return ""
        }
        return String(image)
    }

    function _itemCategory(item) {
        if (!item || typeof item !== "object") {
            return ""
        }
        let category = item[control.categoryRole]
        if (category === undefined || category === null) {
            return ""
        }
        return String(category)
    }

    function _resolveImage(source) {
        return source ? App.Globals.assetPath(source) : ""
    }

    readonly property var _currentItem: control._modelItemAt(control.currentIndex)
    readonly property string _currentLabel: control._itemLabel(control._currentItem)
    readonly property string _currentImage: control._itemImage(control._currentItem)

    property var groupedItems: {
        let groups = []
        let map = {}
        let total = control._modelCount()
        for (let i = 0; i < total; ++i) {
            let item = control._modelItemAt(i)
            let category = control._itemCategory(item)
            let key = category || ""
            if (!map[key]) {
                map[key] = { title: category, items: [] }
                groups.push(map[key])
            }
            map[key].items.push({ index: i, item: item })
        }
        return groups
    }

    readonly property int effectiveCellSize: {
        if (control.columns > 0) {
            let spacing = 8
            let availableWidth = control.popup.availableWidth > 0 ? control.popup.availableWidth : control.popup.width
            let size = Math.floor((availableWidth - (control.columns - 1) * spacing) / control.columns)
            return Math.max(40, size)
        }
        return control.cellSize
    }

    readonly property int effectiveIconSize: Math.min(control.iconSize, control.effectiveCellSize - 8)

    contentItem: Item {
        implicitHeight: Math.max(32, row.implicitHeight)

        RowLayout {
            id: row
            anchors.fill: parent
            anchors.leftMargin: 6
            anchors.rightMargin: control.indicator.width + control.spacing + 6
            spacing: 6

            Image {
                Layout.preferredWidth: 40
                Layout.preferredHeight: 40
                visible: control._currentImage.length > 0
                source: control._resolveImage(control._currentImage)
                fillMode: Image.PreserveAspectFit
                smooth: true
            }

            Label {
                Layout.fillWidth: true
                text: control._currentLabel
                visible: control.showLabel && control._currentLabel.length > 0
                color: control.enabled ? control.palette.text : control.palette.placeholderText
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
        }
    }

    popup.width: control.width
    popup.topMargin: 8
    popup.bottomMargin: 8
    popup.leftPadding: control.popupPadding
    popup.rightPadding: control.popupPadding
    popup.topPadding: control.popupPadding
    popup.bottomPadding: control.popupPadding

    readonly property real __targetHeight: {
        let contentHeight = popupFlickable.implicitHeight
        let cap = control.popupMaxHeight > 0 ? control.popupMaxHeight : contentHeight
        let windowCap = control.Window.height - popup.topMargin - popup.bottomMargin
        return Math.min(contentHeight, cap, windowCap)
    }
    property real __heightScale: 1
    popup.height: __heightScale * __targetHeight

    popup.enter: Transition {
        NumberAnimation { target: control; property: "__heightScale"; from: 0.33; to: 1; easing.type: Easing.OutCubic; duration: 250 }
    }

    popup.contentItem: Flickable {
        id: popupFlickable
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        implicitHeight: contentColumn.implicitHeight

        Column {
            id: contentColumn
            width: popupFlickable.width
            spacing: 12

            Repeater {
                model: control.groupedItems
                delegate: Column {
                    required property var modelData
                    width: contentColumn.width
                    spacing: 8

                    Label {
                        visible: modelData.title && modelData.title.length > 0
                        text: modelData.title || ""
                        color: control.palette.placeholderText
                        leftPadding: 2
                    }

                    Flow {
                        width: parent.width
                        spacing: 8

                        Repeater {
                            model: modelData.items
                            delegate: ItemDelegate {
                                required property var modelData
                                readonly property int itemIndex: modelData.index
                                readonly property var itemData: modelData.item
                                readonly property string itemLabel: control._itemLabel(itemData)
                                readonly property string itemImage: control._itemImage(itemData)
                                readonly property int contentSpacing: 6
                                readonly property int labelHeight: (control.showLabel && itemLabel.length > 0)
                                    ? Math.max(label.implicitHeight, 14)
                                    : 0

                                implicitWidth: control.effectiveCellSize
                                width: implicitWidth
                                implicitHeight: control.effectiveCellSize
                                    + (labelHeight > 0 ? labelHeight + contentSpacing + 2 : 0)
                                height: implicitHeight
                                hoverEnabled: true
                                highlighted: itemIndex === control.currentIndex
                                leftPadding: 0
                                rightPadding: 0
                                topPadding: 0
                                bottomPadding: 0

                                background: Item { }

                                contentItem: Column {
                                    anchors.top: parent.top
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    anchors.topMargin: 2
                                    width: parent.width
                                    spacing: contentSpacing

                                    Rectangle {
                                        id: cellBackground
                                        width: control.effectiveCellSize
                                        height: control.effectiveCellSize
                                        radius: control.cellRadius
                                        color: highlighted
                                            ? control.palette.highlight
                                            : hovered
                                                ? control.palette.midlight
                                                : "transparent"
                                        border.color: "transparent"

                                        Image {
                                            anchors.centerIn: parent
                                            width: control.effectiveIconSize
                                            height: control.effectiveIconSize
                                            source: control._resolveImage(itemImage)
                                            fillMode: Image.PreserveAspectFit
                                            smooth: true
                                        }
                                    }

                                    Label {
                                        id: label
                                        visible: control.showLabel && itemLabel.length > 0
                                        text: itemLabel
                                        width: parent.width
                                        horizontalAlignment: Text.AlignHCenter
                                        wrapMode: Text.Wrap
                                        maximumLineCount: 2
                                        elide: Text.ElideRight
                                        color: control.palette.text
                                    }
                                }

                                onClicked: {
                                    control.currentIndex = itemIndex
                                    control.popup.close()
                                    control.activated(itemIndex)
                                }
                            }
                        }
                    }
                }
            }
        }

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
        }
    }
}
