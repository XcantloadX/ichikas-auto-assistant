.pragma library

function asset_path(relativePath) {
    if (!relativePath) {
        return "file:///" + appController.assetsRootPath
    }
    var normalized = String(relativePath).replace(/\\/g, "/")
    return "file:///" + appController.assetsRootPath + "/" + normalized
}
