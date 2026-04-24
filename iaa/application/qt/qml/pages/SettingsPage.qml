import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

PageContainer {
    id: root
    title: "配置"
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
        onClicked: settingsController.saveJson(JSON.stringify(root.draftState))
    }

    property var options: ({})
    property var draftState: ({})
    property string savedSnapshot: "___init___"
    property bool dirty: false
    property bool configReady: false
    property bool refreshingMumu: false
    property int availableShopIndex: -1
    property int selectedShopIndex: -1
    property var availableListView: null
    property var selectedListView: null
    signal showNotice(string kind, string text)

    function deepClone(obj) {
        return JSON.parse(JSON.stringify(obj));
    }

    function stableStringify(obj) {
        function normalize(value) {
            if (Array.isArray(value)) {
                return value.map(normalize);
            }
            if (value && typeof value === "object") {
                var keys = Object.keys(value).sort();
                var out = {};
                for (var i = 0; i < keys.length; ++i) {
                    out[keys[i]] = normalize(value[keys[i]]);
                }
                return out;
            }
            return value;
        }
        return JSON.stringify(normalize(obj));
    }

    function captureSnapshot() {
        return stableStringify(draftState);
    }

    function updateDirty() {
        dirty = captureSnapshot() !== savedSnapshot;
    }

    function hasUnsavedChanges() {
        return dirty;
    }

    function discardChanges() {
        draftState = JSON.parse(savedSnapshot);
        dirty = false;
    }

    function saveChanges() {
        settingsController.saveJson(JSON.stringify(root.draftState));
    }

    function setField(path, value) {
        var target = draftState;
        for (var i = 0; i < path.length - 1; ++i) {
            target = target[path[i]];
        }
        target[path[path.length - 1]] = value;
        root.draftState = JSON.parse(JSON.stringify(root.draftState));
        updateDirty();
    }

    function isConfigRenderable(config) {
        return !!(config && config.game && config.live && config.challengeLive && config.cm && config.eventShop && config.telemetry);
    }

    function loadState() {
        root.configReady = false;
        root.options = ({});
        root.draftState = ({});

        var loadedOptions = JSON.parse(settingsController.optionsJson());
        var loadedState = JSON.parse(settingsController.stateJson());
        if (loadedOptions && typeof loadedOptions === "object") {
            root.options = loadedOptions;
        }
        if (isConfigRenderable(loadedState)) {
            var state = deepClone(loadedState);

            if (!state.eventShop.selectedItems) {
                state.eventShop.selectedItems = [];
            }
            if (state.game.server === "tw") {
                state.game.linkAccount = "no";
            }

            root.draftState = state;
            root.savedSnapshot = captureSnapshot();
            root.dirty = false;
            root.configReady = true;
        }
    }

    function refreshMumu(showNotice) {
        var shouldNotify = showNotice === undefined ? true : !!showNotice;
        root.refreshingMumu = true;
        // root.showNotice("info", "正在获取 MuMu 实例列表...");

        Qt.callLater(function() {
            var emulator = (root.draftState && root.draftState.game) ? root.draftState.game.emulator : "";
            var preferredId = (root.draftState && root.draftState.game) ? (root.draftState.game.mumuInstanceId || "") : "";
            var ret = settingsController.refreshMumuInstancesJsonFor(emulator, preferredId);
            console.log('mumu ret', ret);
            var payload = JSON.parse(ret);
            if (root.options && typeof root.options === "object") {
                var newOptions = JSON.parse(JSON.stringify(root.options));
                newOptions.mumuInstances = payload.items;
                root.options = newOptions;
            }
            if (payload.selectedId !== preferredId && shouldNotify) {
                root.showNotice("warning", "当前已选 MuMu 实例不可用，请重新选择后保存");
            }
            if (shouldNotify) {
                root.showNotice(payload.ok ? "success" : "error", payload.statusText);
            }
            root.refreshingMumu = false;
        });
    }

    function availableShopItems() {
        var selected = root.draftState.eventShop.selectedItems || [];
        return (root.options.eventShopItems || []).filter(function (item) {
            return selected.indexOf(item.value) < 0;
        });
    }

    function selectedShopItems() {
        var selected = root.draftState.eventShop.selectedItems || [];
        var allItems = root.options.eventShopItems || [];
        return selected.map(function (itemId) {
            for (let i = 0; i < allItems.length; ++i) {
                if (allItems[i].value === itemId) {
                    return allItems[i];
                }
            }
            return {
                value: itemId,
                label: itemId
            };
        });
    }

    function indexOfRole(items, roleName, roleValue) {
        var list = items || [];
        for (let i = 0; i < list.length; ++i) {
            let row = list[i];
            if (row && row[roleName] === roleValue) {
                return i;
            }
        }
        return list.length > 0 ? 0 : -1;
    }

    function moveToSelected() {
        var available = availableShopItems();
        if (root.availableShopIndex < 0 || root.availableShopIndex >= available.length)
            return;
        var scrollY = root.selectedListView ? root.selectedListView.contentY : 0;
        var selected = (draftState.eventShop.selectedItems || []).slice();
        selected.push(available[root.availableShopIndex].value);
        root.setField(["eventShop", "selectedItems"], selected);
        root.availableShopIndex = -1;
        if (root.selectedListView) {
            Qt.callLater(function() { root.selectedListView.contentY = scrollY; });
        }
    }

    function moveToAvailable() {
        var selected = (draftState.eventShop.selectedItems || []).slice();
        if (root.selectedShopIndex < 0 || root.selectedShopIndex >= selected.length)
            return;
        var scrollY = root.availableListView ? root.availableListView.contentY : 0;
        selected.splice(root.selectedShopIndex, 1);
        root.setField(["eventShop", "selectedItems"], selected);
        root.selectedShopIndex = -1;
        if (root.availableListView) {
            Qt.callLater(function() { root.availableListView.contentY = scrollY; });
        }
    }

    function moveSelectedUp() {
        var selected = (draftState.eventShop.selectedItems || []).slice();
        if (root.selectedShopIndex <= 0 || root.selectedShopIndex >= selected.length)
            return;
        var scrollY = root.selectedListView ? root.selectedListView.contentY : 0;
        var item = selected[root.selectedShopIndex];
        selected.splice(root.selectedShopIndex, 1);
        selected.splice(root.selectedShopIndex - 1, 0, item);
        root.setField(["eventShop", "selectedItems"], selected);
        root.selectedShopIndex -= 1;
        if (root.selectedListView) {
            Qt.callLater(function() { root.selectedListView.contentY = scrollY; });
        }
    }

    function moveSelectedDown() {
        var selected = (draftState.eventShop.selectedItems || []).slice();
        if (root.selectedShopIndex < 0 || root.selectedShopIndex >= selected.length - 1)
            return;
        var scrollY = root.selectedListView ? root.selectedListView.contentY : 0;
        var item = selected[root.selectedShopIndex];
        selected.splice(root.selectedShopIndex, 1);
        selected.splice(root.selectedShopIndex + 1, 0, item);
        root.setField(["eventShop", "selectedItems"], selected);
        root.selectedShopIndex += 1;
        if (root.selectedListView) {
            Qt.callLater(function() { root.selectedListView.contentY = scrollY; });
        }
    }

    Component.onCompleted: {
        loadState();
        // refreshMumu(false);
    }

    Connections {
        target: settingsController
        function onOperationSucceeded(text) {
            root.savedSnapshot = root.stableStringify(root.draftState);
            root.dirty = false;
            root.showNotice("success", text);
        }
        function onOperationFailed(text) {
            root.showNotice("error", text);
        }
        function onConfigSwitched() {
            root.loadState();
        }
    }

    Loader {
        anchors.fill: parent
        active: root.configReady
        sourceComponent: settingsContent
    }

    Component {
        id: settingsContent

        ScrollView {
            id: settingsScroll
            anchors.fill: parent
            clip: true
            contentWidth: availableWidth

            ColumnLayout {
                width: settingsScroll.availableWidth
                spacing: 16

                GroupBox {
                    Layout.fillWidth: true
                    title: "游戏设置"

                    ColumnLayout {
                        anchors.fill: parent

                        FormField {
                            labelText: "模拟器类型"
                            SegmentedButton {
                                Layout.fillWidth: true
                                model: root.options.emulators || []
                                textRole: "label"
                                valueRole: "value"
                                currentIndex: root.indexOfRole(root.options.emulators, "value", root.draftState.game.emulator)
                                onActivated: function(index, value) {
                                    root.setField(["game", "emulator"], value);
                                    if (value === "mumu" || value === "mumu_v5") {
                                        refreshMumu(false);
                                    }
                                }
                            }
                        }

                        FormField {
                            labelText: "多开实例"
                            visible: root.draftState.game.emulator === "mumu" || root.draftState.game.emulator === "mumu_v5"
                            RowLayout {
                                ComboBox {
                                    Layout.fillWidth: true
                                    enabled: !root.refreshingMumu
                                    model: root.options.mumuInstances || []
                                    textRole: "label"
                                    valueRole: "id"
                                    currentIndex: root.indexOfRole(root.options.mumuInstances, "id", root.draftState.game.mumuInstanceId)
                                    onActivated: root.setField(["game", "mumuInstanceId"], currentValue)
                                }
                                Button {
                                    text: root.refreshingMumu ? "获取中..." : "刷新"
                                    enabled: !root.refreshingMumu
                                    onClicked: refreshMumu(true)
                                }
                            }
                        }

                        FormField {
                            labelText: "ADB 序列号"
                            visible: root.draftState.game.emulator === "physical_android"
                            TextField {
                                Layout.fillWidth: true
                                text: root.draftState.game.physicalAndroidSerial
                                placeholderText: "留空自动选择第一个 USB 设备"
                                onTextEdited: root.setField(["game", "physicalAndroidSerial"], text)
                            }
                        }

                        FormField {
                            labelText: "ADB IP"
                            visible: root.draftState.game.emulator === "custom"
                            TextField {
                                Layout.fillWidth: true
                                text: root.draftState.game.customAdbIp
                                onTextEdited: root.setField(["game", "customAdbIp"], text)
                            }
                        }

                        FormField {
                            labelText: "ADB 端口"
                            visible: root.draftState.game.emulator === "custom"
                            TextField {
                                Layout.fillWidth: true
                                text: root.draftState.game.customAdbPort
                                onTextEdited: root.setField(["game", "customAdbPort"], text)
                            }
                        }

                        FormField {
                            labelText: "模拟器路径"
                            visible: root.draftState.game.emulator === "custom"
                            TextField {
                                Layout.fillWidth: true
                                text: root.draftState.game.customEmulatorPath
                                onTextEdited: root.setField(["game", "customEmulatorPath"], text)
                            }
                        }

                        FormField {
                            labelText: "启动参数"
                            visible: root.draftState.game.emulator === "custom"
                            TextField {
                                Layout.fillWidth: true
                                text: root.draftState.game.customEmulatorArgs
                                onTextEdited: root.setField(["game", "customEmulatorArgs"], text)
                            }
                        }

                        FormField {
                            labelText: "服务器"
                            SegmentedButton {
                                Layout.fillWidth: true
                                model: root.options.servers || []
                                textRole: "label"
                                valueRole: "value"
                                currentIndex: root.indexOfRole(root.options.servers, "value", root.draftState.game.server)
                                onActivated: function(index, value) {
                                    root.setField(["game", "server"], value);
                                    if (value === "tw") {
                                        root.setField(["game", "linkAccount"], "no");
                                    }
                                }
                            }
                        }

                        FormField {
                            labelText: "引继账号"
                            SegmentedButton {
                                Layout.fillWidth: true
                                enabled: root.draftState.game.server !== "tw"
                                model: root.options.linkAccounts || []
                                textRole: "label"
                                valueRole: "value"
                                currentIndex: root.indexOfRole(root.options.linkAccounts, "value", root.draftState.game.linkAccount)
                                onActivated: function(index, value) {
                                    root.setField(["game", "linkAccount"], value)
                                }
                            }
                        }

                        FormField {
                            labelText: "控制方式"
                            SegmentedButton {
                                Layout.fillWidth: true
                                model: root.options.controlImpls || []
                                textRole: "label"
                                valueRole: "value"
                                currentIndex: root.indexOfRole(root.options.controlImpls, "value", root.draftState.game.controlImpl)
                                onActivated: function(index, value) {
                                    root.setField(["game", "controlImpl"], value)
                                }
                            }
                        }

                        CheckBox {
                            visible: root.draftState.game.controlImpl === "scrcpy"
                            text: "使用虚拟显示器"
                            checked: root.draftState.game.scrcpyVirtualDisplay
                            onToggled: root.setField(["game", "scrcpyVirtualDisplay"], checked)
                        }

                        FormField {
                            labelText: "分辨率设置"
                            RowLayout {
                                ComboBox {
                                    Layout.fillWidth: true
                                    model: root.options.resolutionMethods || []
                                    textRole: "label"
                                    valueRole: "value"
                                    currentIndex: root.indexOfRole(root.options.resolutionMethods, "value", root.draftState.game.resolutionMethod)
                                    onActivated: root.setField(["game", "resolutionMethod"], currentValue)
                                }
                                Button {
                                    text: "恢复分辨率"
                                    onClicked: settingsController.resetResolution()
                                }
                            }
                        }

                        CheckBox {
                            text: "检查并启动模拟器"
                            checked: root.draftState.game.checkEmulator
                            onToggled: root.setField(["game", "checkEmulator"], checked)
                        }
                    }
                }

                GroupBox {
                    Layout.fillWidth: true
                    title: "演出设置"

                    ColumnLayout {
                        anchors.fill: parent
                        FormField {
                            labelText: "歌曲名称"
                            ComboBox {
                                Layout.fillWidth: true
                                model: options.songNames || []
                                currentIndex: Math.max(0, model.indexOf(draftState.live.songName))
                                onActivated: root.setField(["live", "songName"], model[index])
                            }
                        }

                        FormField {
                            labelText: "AP 倍率"
                            ComboBox {
                                Layout.fillWidth: true
                                model: options.apMultipliers || []
                                currentIndex: Math.max(0, model.indexOf(draftState.live.apMultiplier))
                                onActivated: root.setField(["live", "apMultiplier"], model[index])
                            }
                        }
                        CheckBox {
                            text: "自动编队"
                            checked: draftState.live.autoSetUnit
                            onToggled: root.setField(["live", "autoSetUnit"], checked)
                        }
                        CheckBox {
                            text: "追加一次 FullCombo 演出"
                            checked: draftState.live.appendFc
                            onToggled: root.setField(["live", "appendFc"], checked)
                        }
                        CheckBox {
                            text: "追加一首随机歌曲"
                            checked: draftState.live.appendRandom
                            onToggled: root.setField(["live", "appendRandom"], checked)
                        }
                    }
                }

                GroupBox {
                    Layout.fillWidth: true
                    title: "挑战演出设置"

                    ColumnLayout {
                        anchors.fill: parent
                        FormField {
                            labelText: "角色"
                            ComboBox {
                                Layout.fillWidth: true
                                model: options.challengeCharacters || []
                                textRole: "label"
                                valueRole: "value"
                                currentIndex: {
                                    var selected = draftState.challengeLive.characters || [];
                                    if (selected.length > 0) {
                                        var target = selected[0];
                                        for (var i = 0; i < model.length; i++) {
                                            if (model[i].value === target) {
                                                return i;
                                            }
                                        }
                                    }
                                    return -1;
                                }
                                onActivated: root.setField(["challengeLive", "characters"], [model[index].value])
                            }
                        }
                        FormField {
                            labelText: "奖励"
                            ComboBox {
                                Layout.fillWidth: true
                                model: options.challengeAwards || []
                                textRole: "label"
                                valueRole: "value"
                                currentIndex: {
                                    var target = draftState.challengeLive.award;
                                    for (var i = 0; i < model.length; i++) {
                                        if (model[i].value === target) {
                                            return i;
                                        }
                                    }
                                    return -1;
                                }
                                onActivated: root.setField(["challengeLive", "award"], model[index].value)
                            }
                        }
                    }
                }

                GroupBox {
                    Layout.fillWidth: true
                    title: "CM 设置"

                    FormField {
                        labelText: "广告等待秒数"
                        TextField {
                            Layout.fillWidth: true
                            text: draftState.cm.watchAdWaitSec
                            onTextEdited: root.setField(["cm", "watchAdWaitSec"], text)
                        }
                    }
                }

                GroupBox {
                    Layout.fillWidth: true
                    title: "活动商店设置"

                    RowLayout {
                        anchors.fill: parent
                        spacing: 10

                        ListView {
                            id: selectedList
                            Layout.fillWidth: true
                            Layout.preferredHeight: 220
                            model: selectedShopItems()
                            clip: true
                            delegate: ItemDelegate {
                                width: ListView.view.width
                                highlighted: index === root.selectedShopIndex
                                text: modelData.label
                                onClicked: root.selectedShopIndex = index
                            }
                            Component.onCompleted: root.selectedListView = selectedList
                        }

                        ColumnLayout {
                            Button {
                                text: "← 添加"
                                onClicked: root.moveToSelected()
                            }
                            Button {
                                text: "移除 →"
                                onClicked: root.moveToAvailable()
                            }
                            Button {
                                text: "上移"
                                onClicked: root.moveSelectedUp()
                            }
                            Button {
                                text: "下移"
                                onClicked: root.moveSelectedDown()
                            }
                        }

                        ListView {
                            id: availableList
                            Layout.fillWidth: true
                            Layout.preferredHeight: 220
                            model: availableShopItems()
                            clip: true
                            delegate: ItemDelegate {
                                width: ListView.view.width
                                highlighted: index === root.availableShopIndex
                                text: modelData.label
                                onClicked: root.availableShopIndex = index
                            }
                            Component.onCompleted: root.availableListView = availableList
                        }
                    }
                }

                GroupBox {
                    Layout.fillWidth: true
                    title: "数据收集"

                    CheckBox {
                        text: "自动发送匿名错误报告"
                        checked: draftState.telemetry.sentry
                        onToggled: root.setField(["telemetry", "sentry"], checked)
                    }
                }
            }
        }
    }
}
