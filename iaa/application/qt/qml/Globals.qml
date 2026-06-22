pragma Singleton
import QtQuick

QtObject {
    readonly property string language: i18nController ? i18nController.language : "zh_CN"

    function t(key) {
        language
        return i18nController ? i18nController.t(key) : key
    }

    function taskName(taskId, fallback) {
        var key = "task." + taskId
        var translated = t(key)
        return translated === key ? (fallback || taskId) : translated
    }

    function assetPath(relativePath) {
        if (!relativePath) {
            return "file:///" + appController.assetsRootPath
        }
        var s = String(relativePath)
        if (s.indexOf("://") >= 0 || s.startsWith("qrc:/")) {
            return s
        }
        return "file:///" + appController.assetsRootPath + "/" + s.replace(/\\/g, "/")
    }
}
