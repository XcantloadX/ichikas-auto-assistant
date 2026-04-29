import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

PageContainer {
    id: root
    title: "日志"
    property var logBridge
    property int maxLines: 2000
    property string pendingText: ""
    property var logLines: []
    property bool wrapEnabled: true
    property int lineHeightPx: 24
    readonly property bool darkTheme: {
        if (Qt.styleHints.colorScheme === Qt.ColorScheme.Dark) {
            return true
        }
        else {
            return false
        }
    }

    headerActions: RowLayout {
        spacing: 10
        CheckBox {
            text: "自动换行"
            checked: root.wrapEnabled
            onToggled: root.wrapEnabled = checked
        }
        Button {
            text: "清空"
            onClicked: {
                root.logLines = []
                logView.text = ""
                root.pendingText = ""
            }
        }
        Label { text: "最多保留 " + root.maxLines + " 行" }
    }

    function resolveColor(line, streamName) {
        var colors = {
            normal: root.darkTheme ? "#e5e7eb" : "#111827",
            debug: root.darkTheme ? "#94a3b8" : "#64748b",
            warning: root.darkTheme ? "#f59e0b" : "#b45309",
            error: root.darkTheme ? "#f87171" : "#b91c1c",
            critical: root.darkTheme ? "#ef4444" : "#7f1d1d",
            stderr: root.darkTheme ? "#f87171" : "#b91c1c",
        }
        if (streamName === "stderr") {
            return colors.stderr
        }
        if (line.indexOf("[CRITICAL]") >= 0 || line.indexOf("CRITICAL") >= 0) {
            return colors.critical
        }
        if (line.indexOf("[ERROR]") >= 0 || line.indexOf("ERROR") >= 0) {
            return colors.error
        }
        if (line.indexOf("[WARNING]") >= 0 || line.indexOf("WARNING") >= 0 || line.indexOf("WARN") >= 0) {
            return colors.warning
        }
        if (line.indexOf("[DEBUG]") >= 0 || line.indexOf("DEBUG") >= 0) {
            return colors.debug
        }
        return colors.normal
    }

    function escapeHtml(text) {
        return text
            .replace(/\t/g, "    ")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;")
    }

    function renderLogView() {
        var whiteSpace = root.wrapEnabled ? "pre-wrap" : "pre"
        var htmlLines = []
        for (var i = 0; i < root.logLines.length; i++) {
            var entry = root.logLines[i]
            var color = root.resolveColor(entry.text, entry.stream)
            var safe = root.escapeHtml(entry.text)
            htmlLines.push(
                '<span style="color:' + color + ';">' + safe + '</span>'
            )
        }
        logView.text = '<div style="white-space:' + whiteSpace + '; line-height:' + root.lineHeightPx + 'px;">'
            + htmlLines.join("\n") + '</div>'
        Qt.callLater(function() {
            var bar = scrollView.ScrollBar.vertical
            bar.position = Math.max(0, 1.0 - bar.size)
        })
    }

    function appendText(text, streamName) {
        if (!text) {
            return
        }
        var combined = root.pendingText + text
        var parts = combined.split(/\r?\n/)
        root.pendingText = parts.pop()
        for (var i = 0; i < parts.length; i++) {
            root.logLines.push({ text: parts[i], stream: streamName })
        }
        while (root.logLines.length > root.maxLines) {
            root.logLines.shift()
        }
        root.renderLogView()
    }

    onWrapEnabledChanged: {
        root.renderLogView()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        GroupBox {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "输出"

            ScrollView {
                id: scrollView
                anchors.fill: parent
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AsNeeded
                ScrollBar.vertical.policy: ScrollBar.AsNeeded
                background: Rectangle {
                    color: root.palette.base
                    radius: 6
                }

                WheelHandler {
                    acceptedModifiers: Qt.ShiftModifier
                    acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                    target: null
                    blocking: true

                    onWheel: function(event) {
                        if (root.wrapEnabled || logView.width <= scrollView.availableWidth) {
                            return
                        }
                        var delta = 0
                        if (event.pixelDelta.y !== 0) {
                            delta = event.pixelDelta.y
                        } else {
                            delta = event.angleDelta.y / 120 * 48
                        }
                        var bar = scrollView.ScrollBar.horizontal
                        var maxPos = Math.max(0, 1.0 - bar.size)
                        bar.position = Math.max(0, Math.min(maxPos, bar.position - delta / logView.width))
                        event.accepted = true
                    }
                }

                TextArea {
                    id: logView
                    width: root.wrapEnabled ? scrollView.availableWidth : Math.max(implicitWidth, scrollView.availableWidth)
                    height: Math.max(implicitHeight, scrollView.availableHeight)
                    textFormat: TextEdit.RichText
                    wrapMode: root.wrapEnabled ? TextEdit.Wrap : TextEdit.NoWrap
                    verticalAlignment: Text.AlignTop
                    readOnly: true
                    selectByMouse: true
                    selectByKeyboard: true
                    persistentSelection: true
                    font.family: "Consolas"
                    clip: true
                    background: null
                    padding: 8
                }
            }
        }
    }

    Connections {
        target: root.logBridge
        function onTextWritten(text, streamName) {
            root.appendText(text, streamName)
        }
    }
}
