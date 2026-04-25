pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../components"
import "../dsl"

PageContainer {
    id: root
    title: "设置"

    titleRightContent: Rectangle {
        visible: root.dirty
        color: "#FFEBE9"
        border.color: "#DC3545"
        radius: 4
        implicitHeight: 32
        width: labelId.implicitWidth + 16

        Label {
            id: labelId
            text: "有未保存改动"
            color: "#DC3545"
            font.bold: true
            anchors.centerIn: parent
        }
    }

    headerActions: Button {
        text: "保存"
        highlighted: true
        enabled: root.runtimeReady
        onClicked: root.prefsController.save()
    }

    required property var prefsController
    property var runtime: ({"groups": []})
    property bool dirty: false
    property bool runtimeReady: false

    signal showNotice(string kind, string text)

    function loadRuntime() {
        var payload = JSON.parse(root.prefsController.getRuntime())
        if (!payload || typeof payload !== "object") {
            return
        }
        root.runtime = payload
        root.dirty = !!payload.dirty
        root.runtimeReady = true
    }

    function hasUnsavedChanges() {
        return root.prefsController.isDirty()
    }

    function discardChanges() {
        root.prefsController.discard()
    }

    function saveChanges() {
        root.prefsController.save()
    }

    Component.onCompleted: {
        loadRuntime()
    }

    Connections {
        target: root.prefsController

        function onRuntimeChanged() {
            root.loadRuntime()
        }

        function onDirtyChanged(value) {
            root.dirty = !!value
        }

        function onOperationSucceeded(text) {
            root.showNotice("success", text)
        }

        function onOperationFailed(text) {
            root.showNotice("error", text)
        }
    }

    Loader {
        anchors.fill: parent
        active: root.runtimeReady
        sourceComponent: runtimeComponent
    }

    Component {
        id: runtimeComponent

        FormPageView {
            runtime: root.runtime
            formController: root.prefsController
        }
    }
}
