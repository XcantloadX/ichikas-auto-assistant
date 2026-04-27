pragma Singleton
import QtQuick

QtObject {
    function assetPath(relativePath) {
        if (!relativePath) {
            return "file:///" + appController.assetsRootPath
        }
        var normalized = String(relativePath).replace(/\\/g, "/")
        return "file:///" + appController.assetsRootPath + "/" + normalized
    }
}
