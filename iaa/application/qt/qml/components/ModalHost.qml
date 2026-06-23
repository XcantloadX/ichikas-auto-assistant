pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".." as App

Item {
    id: root
    visible: false

    /** 待显示的弹窗请求队列 */
    property var queue: []
    /** 当前弹窗的回调 */
    property var pendingCallback: null
    /** 当前按钮数据模型 */
    property var buttonsModel: []
    /** 当前弹窗是否已回调 */
    property bool resolved: false
    /** 弹窗是否处于打开或打开中 */
    property bool isOpen: false
    /** 关闭/取消时回调的默认值 */
    property var dismissValue: null
    /** 当前弹窗宽度 */
    property int dialogWidth: 420
    /** 当前弹窗的关闭策略 */
    property int dialogClosePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    /** 当前弹窗标题 */
    property string dialogTitle: ""
    /** 当前弹窗内容（可富文本） */
    property string dialogContent: ""
    /** 内容文本格式 */
    property int dialogTextFormat: Text.RichText

    /**
     * 弹出消息框。如果之前的消息框还没有被关闭，会进入消息队列，在前面的消息都展示完毕后再弹出。
     * @param {object} options - 弹窗配置对象
     *   @param {string} [options.title] - 弹窗标题
     *   @param {string} [options.content] - 弹窗正文（可富文本）
     *   @param {int} [options.textFormat] - 文本格式（如 Text.RichText）
     *   @param {int} [options.width] - 弹窗宽度
     *   @param {int} [options.closePolicy] - 关闭策略（Popup.CloseOnEscape 等）
     *   @param {var} [options.dismissValue] - 关闭/取消时的回调值
     *   @param {array} [options.buttons] - 按钮数组，元素可为字符串或对象
     * @param {function} callback - 回调函数，入参为用户选择的 value 或 dismissValue
     */
    function message(options, callback) {
        var payload = { options: options || {}, callback: callback }
        if (root.isOpen) {
            root.queue.push(payload)
            return
        }
        root._present(payload)
    }

    /** 解析 options 并显示弹窗 */
    function _present(payload) {
        var options = payload.options || {}
        root.pendingCallback = typeof payload.callback === "function" ? payload.callback : null
        root.dialogTitle = options.title ? String(options.title) : ""
        root.dialogContent = options.content !== undefined ? String(options.content) : ""
        root.dialogTextFormat = options.textFormat !== undefined ? options.textFormat : Text.RichText
        root.dialogWidth = options.width !== undefined ? options.width : 420
        root.dialogClosePolicy = options.closePolicy !== undefined
            ? options.closePolicy
            : Popup.CloseOnEscape | Popup.CloseOnPressOutside
        root.dismissValue = options.dismissValue !== undefined ? options.dismissValue : null

        var buttons = []
        if (options.buttons && Array.isArray(options.buttons) && options.buttons.length > 0) {
            buttons = options.buttons
        } else {
            buttons = [{ text: App.Globals.t("common.ok"), value: "ok", highlighted: true }]
        }

        root.buttonsModel = buttons
        root.resolved = false
        root.isOpen = true
        modalDialog.open()
    }

    /** 以指定结果结束弹窗并回调 */
    function _resolve(value) {
        if (root.resolved) {
            return
        }
        root.resolved = true
        var cb = root.pendingCallback
        root.pendingCallback = null
        modalDialog.close()
        if (cb) {
            cb(value)
        }
    }

    /** 处理关闭后的回调与队列继续 */
    function _handleClosed() {
        root.isOpen = false
        if (!root.resolved) {
            root.resolved = true
            var cb = root.pendingCallback
            root.pendingCallback = null
            if (cb) {
                cb(root.dismissValue)
            }
        }
        if (root.queue.length > 0) {
            root._present(root.queue.shift())
        }
    }

    Dialog {
        id: modalDialog
        modal: true
        standardButtons: Dialog.NoButton
        anchors.centerIn: Overlay.overlay
        width: root.dialogWidth
        closePolicy: root.dialogClosePolicy
        title: root.dialogTitle

        contentItem: ColumnLayout {
            spacing: 12

            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                textFormat: root.dialogTextFormat
                text: root.dialogContent
            }

            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: 8

                Repeater {
                    model: root.buttonsModel
                    delegate: Button {
                        required property var modelData
                        text: typeof modelData === "string" ? modelData : (modelData.text || "")
                        enabled: typeof modelData === "object" ? modelData.enabled !== false : true
                        highlighted: typeof modelData === "object" ? modelData.highlighted === true : false
                        onClicked: {
                            var value = typeof modelData === "object" ? modelData.value : modelData
                            root._resolve(value)
                        }
                    }
                }
            }
        }

        onClosed: root._handleClosed()
    }

    Component.onCompleted: App.Modal.registerHost(root)
    Component.onDestruction: App.Modal.registerHost(null)
}
