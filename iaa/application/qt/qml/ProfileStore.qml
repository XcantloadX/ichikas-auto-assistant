pragma Singleton
import QtQuick
import IaaApp 1.0

Item {
    id: root
    visible: false

    readonly property var backend: ProfileStoreBackend
    readonly property string currentProfileName: backend ? backend.currentProfileName : "default"
    readonly property string profilesJson: backend ? backend.profilesJson : "{\"profiles\":[]}"

    signal currentProfileChanged()
    signal profilesChanged()

    Connections {
        target: root.backend

        function onCurrentProfileChanged() {
            root.currentProfileChanged()
        }

        function onProfilesChanged() {
            root.profilesChanged()
        }
    }
}
