import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: root
    modal: true
    title: "自动演出"
    width: 620
    anchors.centerIn: Overlay.overlay
    property var presets: []
    signal showNotice(string kind, string text)

    function defaultPayload() {
        return {
            countMode: "specify",
            count: "10",
            loopMode: "list",
            playMode: "game_auto",
            debugEnabled: false,
            autoSetUnit: false,
            apMultiplier: "保持现状",
            songName: "保持不变"
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
            songName: preset.songName || "保持不变"
        }
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
            Label { text: "预设" }
            Repeater {
                model: root.presets
                delegate: Button {
                    text: modelData.name
                    onClicked: root.applyPreset(modelData)
                }
            }
            Button {
                text: "上次设定"
                onClicked: {
                    var raw = runController.lastAutoPresetJson()
                    if (!raw) {
                        root.showNotice("error", "没有找到上次设定")
                        return
                    }
                    root.applyPreset(JSON.parse(raw))
                }
            }
        }

        RowLayout {
            Label { text: "演出次数" }
            RadioButton {
                text: "指定次数"
                checked: formData.countMode === "specify"
                onClicked: formData = Object.assign({}, formData, { countMode: "specify" })
            }
            TextField {
                enabled: formData.countMode === "specify"
                text: formData.count
                placeholderText: "次数"
                onTextEdited: formData = Object.assign({}, formData, { count: text })
            }
            RadioButton {
                text: "直到 AP 耗尽"
                checked: formData.countMode === "all"
                onClicked: formData = Object.assign({}, formData, { countMode: "all" })
            }
        }

        RowLayout {
            Label { text: "循环模式" }
            RadioButton {
                text: "单曲循环"
                checked: formData.loopMode === "single"
                onClicked: formData = Object.assign({}, formData, { loopMode: "single" })
            }
            RadioButton {
                text: "列表顺序"
                checked: formData.loopMode === "list"
                onClicked: formData = Object.assign({}, formData, { loopMode: "list" })
            }
            RadioButton {
                text: "列表随机"
                checked: formData.loopMode === "random"
                onClicked: formData = Object.assign({}, formData, { loopMode: "random" })
            }
        }

        RowLayout {
            Label { text: "自动模式" }
            RadioButton {
                text: "游戏自动"
                checked: formData.playMode === "game_auto"
                onClicked: formData = Object.assign({}, formData, { playMode: "game_auto" })
            }
            RadioButton {
                text: "脚本自动"
                checked: formData.playMode === "script_auto"
                onClicked: formData = Object.assign({}, formData, { playMode: "script_auto", apMultiplier: "0" })
            }
        }

        RowLayout {
            Label { text: "AP 倍率" }
            ComboBox {
                model: ["保持现状", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
                enabled: formData.playMode !== "script_auto"
                currentIndex: model.indexOf(formData.apMultiplier)
                onActivated: formData = Object.assign({}, formData, { apMultiplier: model[currentIndex] })
            }
        }

        RowLayout {
            Label { text: "歌曲名称" }
            ComboBox {
                Layout.fillWidth: true
                model: ["保持不变", "メルト", "独りんぼエンヴィー"]
                editable: true
                enabled: formData.loopMode === "single"
                currentIndex: Math.max(0, model.indexOf(formData.songName))
                onActivated: formData = Object.assign({}, formData, { songName: model[currentIndex] })
                onEditTextChanged: formData = Object.assign({}, formData, { songName: editText })
            }
        }

        CheckBox {
            text: "调试显示（脚本自动）"
            checked: formData.debugEnabled
            onToggled: formData = Object.assign({}, formData, { debugEnabled: checked })
        }
        CheckBox {
            text: "自动编队"
            checked: formData.autoSetUnit
            onToggled: formData = Object.assign({}, formData, { autoSetUnit: checked })
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            Button { text: "取消"; onClicked: root.close() }
            Button {
                text: "开始"
                highlighted: true
                onClicked: {
                    try {
                        runController.runAutoLive(JSON.stringify(root.formData))
                        root.close()
                    } catch (error) {
                        root.showNotice("error", String(error))
                    }
                }
            }
        }
    }
}
