pragma Singleton
import QtQuick

/**
 * 系统剪贴板辅助单例。QML 没有独立的 Clipboard 类型，借助隐藏的 TextEdit.copy() 实现。
 * 用法：App.Clipboard.copyText("要复制的内容")
 */
Item {
    id: root
    visible: false

    TextEdit {
        id: helper
        visible: false
    }

    function copyText(text) {
        helper.text = String(text)
        helper.selectAll()
        helper.copy()
    }
}
