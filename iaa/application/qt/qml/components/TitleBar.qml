import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import ".." as App
import IaaApp 1.0

// 主窗口标题区外壳。
//
// 两种模式通过 prefsMode 切换：
//   prefsMode=false → TabStrip（tab 栏，Chrome 风格）
//   prefsMode=true  → PageHeader（返回按钮 + 图标 + 标题）
//
// 公共部分（背景、顶部拖拽条、WindowControls、tab 关闭 dirty 对话框）
// 由本组件统一管理。
Item {
    id: root

    readonly property int _stripH: 8   // 顶部纯拖拽条高度
    readonly property int _tabH: 34    // tab 行高度
    height: _stripH + _tabH

    required property var configManagerDialog

    // 当前顶层页签（0 = 总览，1 = config tab），由 TabStrip 驱动
    // 外部若需主动切换，调用 setCurrentIndex()
    readonly property int currentIndex: tabStrip.currentIndex

    function setCurrentIndex(index) {
        tabStrip.currentIndex = index
    }

    property bool prefsMode: false

    signal settingsRequested()
    signal backRequested()
    signal minimizeRequested()
    signal closeRequested()

    // 待关闭 tab 的 index（dirty 检查用）
    property int pendingCloseIndex: -1

    // ── Tab 列表数据 ────────────────────────────────────────────────────
    property var _tabs: []
    function _reloadTabs() {
        root._tabs = JSON.parse(TabManager.tabsJson())
    }
    Component.onCompleted: _reloadTabs()

    // ── Chrome 风格 Win32 hit-test 同步 ────────────────────────────────
    // 交互区右边界：prefsMode 时只有返回按钮，否则是完整 tab 行
    Binding {
        target: (typeof tabBarBridge !== 'undefined' && tabBarBridge) ? tabBarBridge : null
        property: "tabInteractiveEnd"
        value: root.prefsMode ? pageHeader.interactiveEnd : tabStrip.interactiveEnd
    }

    // ── TabManager 事件 ────────────────────────────────────────────────
    Connections {
        target: TabManager
        function onTabsChanged()      { root._reloadTabs() }
        function onActiveTabChanged() { root._reloadTabs() }
        function onCloseTabBlocked(reason) { App.Notice.show("error", reason) }
        function onReadyToCloseTab(index) {
            root.pendingCloseIndex = index
            var sc = TabManager.settingsControllerAt(index)
            if (sc && sc.isDirty()) {
                tabCloseUnsavedDialog.open()
            } else {
                TabManager.closeTab(index)
                root.pendingCloseIndex = -1
            }
        }
    }

    // ── 背景 ──────────────────────────────────────────────────────────
    // 颜色由 IaaTheme 统一管理（避免散落的 palette / colorScheme 判断）。
    // prefsMode + 非 solid：全透明，让 Mica/acrylic DWM 背景完整透出。
    Rectangle {
        anchors.fill: parent
        color: (root.prefsMode && !App.IaaTheme.isSolid)
            ? "transparent"
            : App.IaaTheme.titleBg
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 顶部纯拖拽条（HTCAPTION 区域）
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: root._stripH
        }

        // Tab 行内容区（两种子组件叠放，visibility 切换）
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: root._tabH

            TabStrip {
                id: tabStrip
                anchors.fill: parent
                visible: !root.prefsMode
                configManagerDialog: root.configManagerDialog
                tabs: root._tabs
                onSettingsRequested: root.settingsRequested()
            }

            PageHeader {
                id: pageHeader
                anchors.fill: parent
                visible: root.prefsMode
                title: "一歌小助手"
                iconSource: App.Globals.assetPath("ichika_chibi.png")
                onBackRequested: root.backRequested()
            }
        }
    }

    // 窗口控件贴右侧，覆盖完整 TitleBar 高度（含顶部拖拽条）
    WindowControls {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        window: root.Window.window
        onMinimizeRequested: root.minimizeRequested()
        onCloseRequested: root.closeRequested()
    }

    // ── Tab 关闭时的 dirty 检查对话框 ──────────────────────────────────
    Dialog {
        id: tabCloseUnsavedDialog
        modal: true
        title: "未保存更改"
        standardButtons: Dialog.NoButton
        width: 420
        anchors.centerIn: Overlay.overlay

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: "该配置有未保存的更改，关闭 Tab 前请选择处理方式。"
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: 8
                Button {
                    text: "取消"
                    onClicked: {
                        tabCloseUnsavedDialog.close()
                        root.pendingCloseIndex = -1
                    }
                }
                Button {
                    text: "不保存并关闭"
                    onClicked: {
                        var idx = root.pendingCloseIndex
                        tabCloseUnsavedDialog.close()
                        root.pendingCloseIndex = -1
                        if (idx >= 0) {
                            var sc = TabManager.settingsControllerAt(idx)
                            if (sc) sc.discard()
                            TabManager.closeTab(idx)
                        }
                    }
                }
                Button {
                    text: "保存并关闭"
                    highlighted: true
                    onClicked: {
                        var idx = root.pendingCloseIndex
                        tabCloseUnsavedDialog.close()
                        root.pendingCloseIndex = -1
                        if (idx >= 0) {
                            var sc = TabManager.settingsControllerAt(idx)
                            if (sc) sc.save()
                            TabManager.closeTab(idx)
                        }
                    }
                }
            }
        }
    }
}
