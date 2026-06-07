pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQml.Models

import "../components"

ColumnLayout {
    id: root

    required property var field
    required property var formController

    spacing: 4

    // Drag-reorder state
    property int _dragCurrentIndex: -1   // visual index of the item being dragged (-1 = not dragging)
    property var _currentOrder: []       // selected values in current visual order during drag
    readonly property bool _dragging: _dragCurrentIndex >= 0
    property real _autoScrollVelocity: 0 // px/tick; + = scroll down, - = scroll up

    property var normalizedOptions: {
        let options = root.field.options || []
        let out = []
        for (let i = 0; i < options.length; ++i) {
            let item = options[i]
            if (item && typeof item === "object") {
                out.push({
                    value: item.value !== undefined ? item.value : item,
                    label: String(item.label !== undefined && item.label !== null
                        ? item.label
                        : (item.value !== undefined ? item.value : "")),
                    image: String(item.image || item.img || ""),
                    icon: String(item.icon || item.glyph || ""),
                })
            } else {
                let text = String(item)
                out.push({ value: item, label: text, image: "", icon: "" })
            }
        }
        return out
    }

    function _toArray(value) {
        if (!Array.isArray(value)) return []
        let out = []
        for (let i = 0; i < value.length; ++i) {
            let v = value[i]
            out.push((v && typeof v === "object") ? v.value : v)
        }
        return out
    }

    function selectedValues() {
        return root._toArray(root.field.value)
    }

    function selectedItems() {
        let values = root.selectedValues()
        let opts = root.normalizedOptions
        let out = []
        for (let i = 0; i < values.length; ++i) {
            let found = null
            for (let j = 0; j < opts.length; ++j) {
                if (String(opts[j].value) === String(values[i])) {
                    found = opts[j]
                    break
                }
            }
            out.push(found || { value: values[i], label: String(values[i]), image: "", icon: "" })
        }
        return out
    }

    function unselectedItems() {
        let strValues = root.selectedValues().map(function(v) { return String(v) })
        return root.normalizedOptions.filter(function(item) {
            return strValues.indexOf(String(item.value)) < 0
        })
    }

    function _commit(values) {
        root.formController.setValue(root.field.id, values)
    }

    function check(value) {
        let selected = root.selectedValues()
        if (selected.map(String).indexOf(String(value)) >= 0) return
        selected.push(value)
        root._commit(selected)
    }

    function uncheck(value) {
        let selected = root.selectedValues()
        let idx = selected.map(String).indexOf(String(value))
        if (idx < 0) return
        selected.splice(idx, 1)
        root._commit(selected)
    }

    function moveUp(idx) {
        let selected = root.selectedValues()
        if (idx <= 0 || idx >= selected.length) return
        let tmp = selected[idx - 1]
        selected[idx - 1] = selected[idx]
        selected[idx] = tmp
        root._commit(selected)
    }

    function moveDown(idx) {
        let selected = root.selectedValues()
        if (idx < 0 || idx >= selected.length - 1) return
        let tmp = selected[idx + 1]
        selected[idx + 1] = selected[idx]
        selected[idx] = tmp
        root._commit(selected)
    }

    // Move item in both the DelegateModel visual order and the tracking array.
    // Called from onPositionChanged; delegates call this via root.* to stay
    // within ComponentBehavior: Bound scope rules.
    function _moveDelegateItem(from, to) {
        if (from === to) return
        selectedDelegateModel.items.move(from, to)
        let arr = root._currentOrder.slice()
        let item = arr.splice(from, 1)[0]
        arr.splice(to, 0, item)
        root._currentOrder = arr
    }

    // Compute auto-scroll velocity from the mouse Y position (in root coordinates).
    // Called each onPositionChanged; reads/writes _autoScrollVelocity which drives autoScrollTimer.
    function _updateAutoScroll(rootY) {
        let svY = root.mapToItem(scrollView, 0, rootY).y
        let threshold = 30          // px from edge where scrolling starts
        let maxSpeed  = 8           // px per timer tick at the very edge
        let svh = scrollView.height
        if (svY < threshold) {
            root._autoScrollVelocity = -((threshold - Math.max(0, svY)) / threshold) * maxSpeed
        } else if (svY > svh - threshold) {
            root._autoScrollVelocity = ((Math.min(svh, svY) - (svh - threshold)) / threshold) * maxSpeed
        } else {
            root._autoScrollVelocity = 0
        }
    }

    // Fires at ~60 fps while dragging near an edge; nudges the ScrollView content.
    Timer {
        id: autoScrollTimer
        interval: 16
        repeat: true
        running: root._dragging && root._autoScrollVelocity !== 0
        onTriggered: {
            let f = scrollView.contentItem                         // the inner Flickable
            let maxY = Math.max(0, f.contentHeight - f.height)
            f.contentY = Math.max(0, Math.min(f.contentY + root._autoScrollVelocity, maxY))
        }
    }

    // DelegateModel wrapping the selected items list.
    // items.move() reorders delegates live without touching the underlying model,
    // avoiding a full delegate reset during drag.
    DelegateModel {
        id: selectedDelegateModel
        model: root.selectedItems()

        delegate: Item {
            id: delegateRoot
            required property int index
            required property var modelData

            // Current visual position in the DelegateModel (updates after every items.move())
            property int visualIndex: DelegateModel.itemsIndex

            readonly property bool isDragSource:
                root._dragging && root._dragCurrentIndex === delegateRoot.visualIndex

            width: ListView.view.width
            height: rowContent.implicitHeight

            ItemDelegate {
                id: rowContent
                width: parent.width
                enabled: !!root.field.enabled
                onClicked: {
                    if (!root._dragging) root.uncheck(delegateRoot.modelData.value)
                }
                highlighted: delegateRoot.isDragSource
                topPadding: 0
                bottomPadding: 0
                leftPadding: 8
                rightPadding: 4

                contentItem: RowLayout {
                    spacing: 6

                    // Drag grip handle
                    Item {
                        id: gripHandle
                        implicitWidth: 20
                        implicitHeight: 28
                        Layout.alignment: Qt.AlignVCenter
                        visible: !!root.field.enabled
                        opacity: delegateRoot.isDragSource ? 0.4 : 1.0

                        // Three short bars as a visual grip indicator
                        Column {
                            anchors.centerIn: parent
                            spacing: 3
                            Repeater {
                                model: 3
                                delegate: Rectangle {
                                    required property int index
                                    width: 12
                                    height: 2
                                    radius: 1
                                    color: rowContent.palette.mid
                                }
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.SizeVerCursor
                            preventStealing: true

                            onPressed: (mouse) => {
                                root._currentOrder = root.selectedValues().slice()
                                root._dragCurrentIndex = delegateRoot.visualIndex
                                mouse.accepted = true
                            }

                            onPositionChanged: (mouse) => {
                                if (!root._dragging) return
                                // Reorder
                                let lv = delegateRoot.ListView.view
                                let pt = mapToItem(lv, mouseX, mouseY)
                                let h = delegateRoot.height
                                let mouseIdx = Math.max(0, Math.min(
                                    Math.floor(pt.y / h), lv.count - 1))
                                if (mouseIdx !== root._dragCurrentIndex) {
                                    root._moveDelegateItem(root._dragCurrentIndex, mouseIdx)
                                    root._dragCurrentIndex = mouseIdx
                                }
                                // Edge auto-scroll
                                root._updateAutoScroll(mapToItem(root, mouseX, mouseY).y)
                            }

                            onReleased: {
                                root._autoScrollVelocity = 0
                                let order = root._currentOrder
                                root._dragCurrentIndex = -1
                                root._currentOrder = []
                                root._commit(order)
                            }

                            onCanceled: {
                                root._autoScrollVelocity = 0
                                let order = root._currentOrder
                                root._dragCurrentIndex = -1
                                root._currentOrder = []
                                root._commit(order)
                            }
                        }
                    }

                    // Checked indicator: CheckboxComposite (\uE73E) in Segoe MDL2 Assets
                    Text {
                        text: "\uE73E"
                        font.family: "Segoe MDL2 Assets"
                        font.pixelSize: 16
                        color: rowContent.palette.accent
                        Layout.alignment: Qt.AlignVCenter
                    }

                    // Image icon
                    Image {
                        visible: delegateRoot.modelData.image !== ""
                        source: delegateRoot.modelData.image
                        width: 18
                        height: 18
                        fillMode: Image.PreserveAspectFit
                        Layout.alignment: Qt.AlignVCenter
                    }

                    // Glyph icon (caller-supplied, e.g. Segoe Fluent Icons)
                    Text {
                        visible: delegateRoot.modelData.image === "" && delegateRoot.modelData.icon !== ""
                        text: delegateRoot.modelData.icon
                        font.family: "Segoe Fluent Icons"
                        font.pixelSize: 14
                        color: rowContent.palette.text
                        Layout.alignment: Qt.AlignVCenter
                    }

                    Label {
                        Layout.fillWidth: true
                        text: delegateRoot.modelData.label
                    }

                    // Move up: ChevronUp (\uE70E)
                    ToolButton {
                        text: "\uE70E"
                        font.family: "Segoe MDL2 Assets"
                        implicitWidth: 28
                        implicitHeight: 28
                        enabled: delegateRoot.visualIndex > 0 && !!root.field.enabled
                        onClicked: root.moveUp(delegateRoot.visualIndex)
                    }

                    // Move down: ChevronDown (\uE70D)
                    ToolButton {
                        text: "\uE70D"
                        font.family: "Segoe MDL2 Assets"
                        implicitWidth: 28
                        implicitHeight: 28
                        enabled: delegateRoot.visualIndex < selectedDelegateModel.count - 1 && !!root.field.enabled
                        onClicked: root.moveDown(delegateRoot.visualIndex)
                    }
                }
            }
        }
    }

    FormField {
        Layout.fillWidth: true
        labelText: root.field.label
        helpText: root.field.helpText || ""
        errorText: root.field.error || ""

        ScrollView {
            id: scrollView
            Layout.fillWidth: true
            implicitHeight: Math.min(
                contentHeight,
                root.field.props && root.field.props.height ? root.field.props.height : 300
            )
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: scrollView.availableWidth
                spacing: 0

                // ---- Checked/selected items ----
                ListView {
                    id: selectedListView
                    Layout.fillWidth: true
                    implicitHeight: contentHeight
                    interactive: false
                    clip: false
                    model: selectedDelegateModel

                    // Animate the item being explicitly moved
                    move: Transition {
                        NumberAnimation { property: "y"; duration: 150; easing.type: Easing.OutQuad }
                    }

                    // Animate items displaced by a move
                    moveDisplaced: Transition {
                        NumberAnimation { property: "y"; duration: 150; easing.type: Easing.OutQuad }
                    }
                }

                // ---- Divider ----
                Rectangle {
                    visible: root.selectedItems().length > 0 && root.unselectedItems().length > 0
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    Layout.bottomMargin: 4
                    height: 1
                    color: "#20000000"
                }

                // ---- Unchecked/unselected items ----
                Repeater {
                    model: root.unselectedItems()

                    delegate: ItemDelegate {
                        id: unselItem
                        required property int index
                        required property var modelData

                        Layout.fillWidth: true
                        enabled: !!root.field.enabled
                        onClicked: root.check(unselItem.modelData.value)
                        topPadding: 0
                        bottomPadding: 0
                        leftPadding: 8
                        rightPadding: 4

                        contentItem: RowLayout {
                            spacing: 6

                            // Unchecked indicator: Checkbox (\uE739) in Segoe MDL2 Assets
                            Text {
                                text: "\uE739"
                                font.family: "Segoe MDL2 Assets"
                                font.pixelSize: 16
                                color: unselItem.palette.placeholderText
                                Layout.alignment: Qt.AlignVCenter
                            }

                            // Image icon
                            Image {
                                visible: unselItem.modelData.image !== ""
                                source: unselItem.modelData.image
                                width: 18
                                height: 18
                                fillMode: Image.PreserveAspectFit
                                Layout.alignment: Qt.AlignVCenter
                            }

                            // Glyph icon
                            Text {
                                visible: unselItem.modelData.image === "" && unselItem.modelData.icon !== ""
                                text: unselItem.modelData.icon
                                font.family: "Segoe Fluent Icons"
                                font.pixelSize: 14
                                color: unselItem.palette.text
                                Layout.alignment: Qt.AlignVCenter
                            }

                            Label {
                                Layout.fillWidth: true
                                text: unselItem.modelData.label
                            }
                        }
                    }
                }
            }
        }
    }
}
