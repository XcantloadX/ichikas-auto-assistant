pragma Singleton
import QtQuick
import IaaApp 1.0

QtObject {
    function assetPath(relativePath) {
        if (!relativePath) {
            return "file:///" + AppController.assetsRootPath
        }
        var s = String(relativePath)
        if (s.indexOf("://") >= 0 || s.startsWith("qrc:/")) {
            return s
        }
        return "file:///" + AppController.assetsRootPath + "/" + s.replace(/\\/g, "/")
    }
}
