import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".." as App
import "../controls"
import "../components/form"

Dialog {
    id: root
    modal: true
    title: "自动演出"
    width: 620
    anchors.centerIn: Overlay.overlay
    property var runCtrl: null
    property var presets: []

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

    function updateField(key, value) {
        formData = Object.assign({}, formData, { [key]: value })
    }

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
        presets = JSON.parse(root.runCtrl.builtinAutoPresetsJson())
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
                    var raw = root.runCtrl.lastAutoPresetJson()
                    if (!raw) {
                        App.Notice.show("error", "没有找到上次设定")
                        return
                    }
                    root.applyPreset(JSON.parse(raw))
                }
            }
        }

        FormSegmentedButton {
            label: "次数模式"
            options: [
                { label: "指定次数", value: "specify" },
                { label: "直到 AP 耗尽", value: "all" }
            ]
            value: root.formData.countMode
            onUserSelected: function(v) { root.updateField("countMode", v) }
        }

        FormTextField {
            visible: root.formData.countMode === "specify"
            label: "次数"
            value: root.formData.count
            placeholder: "次数"
            onUserEdited: function(v) { root.updateField("count", v) }
        }

        FormSegmentedButton {
            label: "循环模式"
            options: [
                { label: "单曲循环", value: "single" },
                { label: "列表顺序", value: "list" },
                { label: "列表随机", value: "random" }
            ]
            value: root.formData.loopMode
            onUserSelected: function(v) { root.updateField("loopMode", v) }
        }

        FormSegmentedButton {
            label: "自动模式"
            options: [
                { label: "游戏自动", value: "game_auto" },
                { label: "脚本自动", value: "script_auto" }
            ]
            value: root.formData.playMode
            onUserSelected: function(v) {
                root.updateField("playMode", v)
                if (v === "script_auto") {
                    root.updateField("apMultiplier", "0")
                }
            }
        }

        FormComboBox {
            label: "AP 倍率"
            options: [
                { label: "保持现状", value: "保持现状" },
                { label: "0", value: "0" }, { label: "1", value: "1" }, { label: "2", value: "2" },
                { label: "3", value: "3" }, { label: "4", value: "4" }, { label: "5", value: "5" },
                { label: "6", value: "6" }, { label: "7", value: "7" }, { label: "8", value: "8" },
                { label: "9", value: "9" }, { label: "10", value: "10" }
            ]
            value: root.formData.apMultiplier
            enabled: root.formData.playMode !== "script_auto"
            onUserSelected: function(v) { root.updateField("apMultiplier", v) }
        }

        FormNotice {
            visible: root.formData.playMode === "script_auto"
            style: "info"
            content: "为避免滥用，脚本自动时 AP 锁定 0。"
        }

        FormEditableComboBox {
            label: "歌曲名称"
            help: "支持任意绿谱（EASY 难度）。<br>你可以输入任何名称。这里的名称会在游戏内输入到搜索框内，并自动选中第一首歌。"
            options: [
                { label: "保持不变", value: "保持不变" },
                { label: "メルト", value: "メルト" },
                { label: "独りんぼエンヴィー", value: "独りんぼエンヴィー" }
            ]
            value: root.formData.songName
            enabled: root.formData.loopMode === "single"
            onUserSelected: function(v) { root.updateField("songName", v) }
            onUserEdited: function(v) { root.updateField("songName", v) }
        }

        FormCheckBox {
            label: "调试显示（脚本自动）"
            value: root.formData.debugEnabled
            onUserToggled: function(v) { root.updateField("debugEnabled", v) }
        }

        FormCheckBox {
            label: "自动编队"
            value: root.formData.autoSetUnit
            onUserToggled: function(v) { root.updateField("autoSetUnit", v) }
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            Button { text: "取消"; onClicked: root.close() }
            Button {
                text: "开始"
                highlighted: true
                onClicked: {
                    try {
                        root.runCtrl.runAutoLive(JSON.stringify(root.formData))
                        root.close()
                    } catch (error) {
                        App.Notice.show("error", String(error))
                    }
                }
            }
        }
    }
}
