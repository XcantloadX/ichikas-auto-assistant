pragma Singleton
import QtQuick

QtObject {
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
