pragma Singleton
pragma ComponentBehavior: Bound
import QtQuick

QtObject {
    id: root

    property var host: null
    property var pending: []

    function registerHost(hostItem) {
        root.host = hostItem
        root.flushPending()
    }

    /**
     * 弹出「选择型」消息框：标题 + 正文 + 按钮，用户选择后通过 callback 拿到结果。
     * 按钮元素为字符串或 { text, value, enabled, highlighted }，点击即关闭并回调 value。
     * 详见 ModalHost.message()。
     */
    function message(options, callback) {
        root._enqueue("message", options, callback)
    }

    /**
     * 弹出「自定义型」弹窗：内容可替换为任意 QML 组件，按钮自行决定点击行为，不强制走统一回调。
     * 详见 ModalHost.custom()。
     */
    function custom(options) {
        root._enqueue("custom", options, null)
    }

    function _enqueue(kind, options, callback) {
        var payload = { kind: kind, options: options || {}, callback: callback }
        if (!root.host) {
            root.pending.push(payload)
            return
        }
        root.host.show(payload)
    }

    function flushPending() {
        if (!root.host || root.pending.length === 0) {
            return
        }
        var items = root.pending.slice(0)
        root.pending = []
        for (var i = 0; i < items.length; i++) {
            root.host.show(items[i])
        }
    }
}
