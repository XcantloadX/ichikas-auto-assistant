import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".." as App
import "../../../framework/dsl/qml/controls"

Dialog {
    id: root
    modal: true
    title: App.Globals.t("task.auto_live")
    width: 620
    anchors.centerIn: Overlay.overlay
    property var presets: []

    readonly property string apKeepValue: runController.apKeepValue
    readonly property string songKeepValue: runController.songKeepValue

    function defaultPayload() {
        return {
            countMode: "specify",
            count: "10",
            loopMode: "list",
            playMode: "game_auto",
            debugEnabled: false,
            autoSetUnit: false,
            apMultiplier: root.apKeepValue,
            songName: root.songKeepValue
        }
    }

    property var formData: defaultPayload()

    function applyPreset(preset) {
        formData = {
            countMode: preset.countMode,
            count: preset.count,
            loopMode: preset.loopMode,
            playMode: preset.playMode,
            debugEnabled: preset.debugEnabled,
            autoSetUnit: preset.autoSetUnit,
            apMultiplier: preset.apMultiplier,
            songName: preset.songName || root.songKeepValue
        }
    }

    function apMultiplierLabel(value) {
        if (value === root.apKeepValue) {
            return App.Globals.t("auto_live.ap.keep")
        }
        if (value === "maximum") {
            return App.Globals.t("auto_live.ap.maximum")
        }
        return value
    }

    function apMultiplierValue(label) {
        if (label === App.Globals.t("auto_live.ap.keep")) {
            return root.apKeepValue
        }
        if (label === App.Globals.t("auto_live.ap.maximum")) {
            return "maximum"
        }
        return label
    }

    function apMultiplierOptions() {
        return [
            App.Globals.t("auto_live.ap.keep"),
            App.Globals.t("auto_live.ap.maximum"),
            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"
        ]
    }

    function songNameLabel(value) {
        return value === root.songKeepValue ? App.Globals.t("auto_live.song.keep") : value
    }

    function songNameValue(label) {
        return label === App.Globals.t("auto_live.song.keep") ? root.songKeepValue : label
    }

    function songNameOptions() {
        return [
            App.Globals.t("auto_live.song.keep"),
            "メルト",
            "独りんぼエンヴィー"
        ]
    }

    function presetNameLabel(name) {
        return runController.autoLivePresetLabel(name)
    }

    onOpened: {
        presets = JSON.parse(runController.builtinAutoPresetsJson())
        formData = defaultPayload()
    }

    standardButtons: Dialog.NoButton

    contentItem: ColumnLayout {
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            Label { text: App.Globals.t("auto_live.preset") }
            Repeater {
                model: root.presets
                delegate: Button {
                    text: root.presetNameLabel(modelData.name)
                    onClicked: root.applyPreset(modelData)
                }
            }
            Button {
                text: App.Globals.t("auto_live.preset.last")
                onClicked: {
                    var raw = runController.lastAutoPresetJson()
                    if (!raw) {
                        App.Notice.show("error", App.Globals.t("auto_live.notice.no_last_preset"))
                        return
                    }
                    root.applyPreset(JSON.parse(raw))
                }
            }
        }

        RowLayout {
            Label { text: App.Globals.t("auto_live.count") }
            RadioButton {
                text: App.Globals.t("auto_live.count.specify")
                checked: formData.countMode === "specify"
                onClicked: formData = Object.assign({}, formData, { countMode: "specify" })
            }
            TextField {
                enabled: formData.countMode === "specify"
                text: formData.count
                placeholderText: App.Globals.t("auto_live.count.placeholder")
                onTextEdited: formData = Object.assign({}, formData, { count: text })
            }
            RadioButton {
                text: App.Globals.t("auto_live.count.all")
                checked: formData.countMode === "all"
                onClicked: formData = Object.assign({}, formData, { countMode: "all" })
            }
        }

        RowLayout {
            Label { text: App.Globals.t("auto_live.loop_mode") }
            RadioButton {
                text: App.Globals.t("auto_live.loop.single")
                checked: formData.loopMode === "single"
                onClicked: formData = Object.assign({}, formData, { loopMode: "single" })
            }
            RadioButton {
                text: App.Globals.t("auto_live.loop.list")
                checked: formData.loopMode === "list"
                onClicked: formData = Object.assign({}, formData, { loopMode: "list" })
            }
            RadioButton {
                text: App.Globals.t("auto_live.loop.random")
                checked: formData.loopMode === "random"
                onClicked: formData = Object.assign({}, formData, { loopMode: "random" })
            }
        }

        RowLayout {
            Label { text: App.Globals.t("auto_live.play_mode") }
            RadioButton {
                text: App.Globals.t("auto_live.play.game_auto")
                checked: formData.playMode === "game_auto"
                onClicked: formData = Object.assign({}, formData, { playMode: "game_auto" })
            }
            RadioButton {
                text: App.Globals.t("auto_live.play.script_auto")
                checked: formData.playMode === "script_auto"
                onClicked: formData = Object.assign({}, formData, { playMode: "script_auto", apMultiplier: "0" })
            }
        }

        RowLayout {
            Label { text: App.Globals.t("auto_live.ap_multiplier") }
            Select {
                model: root.apMultiplierOptions()
                enabled: formData.playMode !== "script_auto"
                currentIndex: Math.max(0, model.indexOf(root.apMultiplierLabel(formData.apMultiplier)))
                onActivated: formData = Object.assign({}, formData, { apMultiplier: root.apMultiplierValue(model[currentIndex]) })
            }
        }

        RowLayout {
            Label { text: App.Globals.t("auto_live.song_name") }
            ComboBox {
                Layout.fillWidth: true
                model: root.songNameOptions()
                editable: true
                enabled: formData.loopMode === "single"
                currentIndex: Math.max(0, model.indexOf(root.songNameLabel(formData.songName)))
                onActivated: formData = Object.assign({}, formData, { songName: root.songNameValue(model[currentIndex]) })
                onEditTextChanged: formData = Object.assign({}, formData, { songName: root.songNameValue(editText) })
            }
        }

        CheckBox {
            text: App.Globals.t("auto_live.debug_display")
            checked: formData.debugEnabled
            onToggled: formData = Object.assign({}, formData, { debugEnabled: checked })
        }
        CheckBox {
            text: App.Globals.t("auto_live.auto_set_unit")
            checked: formData.autoSetUnit
            onToggled: formData = Object.assign({}, formData, { autoSetUnit: checked })
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            Button { text: App.Globals.t("common.cancel"); onClicked: root.close() }
            Button {
                text: App.Globals.t("common.start")
                highlighted: true
                onClicked: {
                    try {
                        runController.runAutoLive(JSON.stringify(root.formData))
                        root.close()
                    } catch (error) {
                        App.Notice.show("error", String(error))
                    }
                }
            }
        }
    }
}
