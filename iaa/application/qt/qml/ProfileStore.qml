pragma Singleton
import QtQuick

Item {
    id: root
    visible: false

    readonly property var backend: profileStoreBackend
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
