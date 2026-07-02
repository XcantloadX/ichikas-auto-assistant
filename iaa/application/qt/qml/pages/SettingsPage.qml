pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import ".." as App
import "../components"
import "../controls"
import "../../../framework/dsl/qml"

PageContainer {
    id: root
    title: App.Globals.t("nav.config")

    titleRightContent: RowLayout {
        spacing: 8
        Rectangle {
            visible: root.scriptRunning
            color: "#FEF3C7"
            border.color: "#F59E0B"
            radius: 4
            implicitHeight: 32
            width: runningLabel.implicitWidth + 16

            Label {
                id: runningLabel
                text: App.Globals.t("page.settings.script_running")
                color: "#B45309"
                font.bold: true
                anchors.centerIn: parent
            }
        }
        Rectangle {
            visible: root.dirty
            color: "#FFEBE9"
            border.color: "#DC3545"
            radius: 4
            implicitHeight: 32
            width: labelId.implicitWidth + 16

            Label {
                id: labelId
                text: App.Globals.t("common.unsaved_changes")
                color: "#DC3545"
                font.bold: true
                anchors.centerIn: parent
            }
        }
    }

    readonly property bool scriptRunning: runController.running || runController.isStarting || runController.isStopping

    headerActions: Button {
        text: App.Globals.t("common.save")
        highlighted: true
        enabled: root.runtimeReady && !root.scriptRunning
        onClicked: root.formController.save()
    }

    required property var formController
    property var runtime: ({"groups": []})
    property bool dirty: false
    property bool runtimeReady: false

    function loadRuntime() {
        var payload = JSON.parse(root.formController.getRuntime())
        if (!payload || typeof payload !== "object") {
            return
        }
        root.runtime = payload
        root.dirty = !!payload.dirty
        root.runtimeReady = true
    }

    function hasUnsavedChanges() {
        return root.formController.isDirty()
    }

    function discardChanges() {
        root.formController.discard()
    }

    function saveChanges() {
        root.formController.save()
    }

    Component.onCompleted: {
        loadRuntime()
    }

    Connections {
        target: root.formController

        function onRuntimeChanged() {
            root.loadRuntime()
        }

        function onDirtyChanged(value) {
            root.dirty = !!value
        }


        function onConfigSwitched() {
            root.loadRuntime()
        }
    }

    Loader {
        anchors.fill: parent
        active: root.runtimeReady
        enabled: !root.scriptRunning
        sourceComponent: runtimeComponent
    }

    Component {
        id: runtimeComponent

        FormPageView {
            runtime: root.runtime
            formController: root.formController
            extraKinds: ({
                "resolution_select": Qt.resolvedUrl("../controls/DslResolutionSelect.qml")
            })
        }
    }
}
