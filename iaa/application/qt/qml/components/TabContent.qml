import QtQuick
import QtQuick.Layouts
import ".." as App
import "../pages"
import "../dialogs"

Item {
    id: root

    property var runCtrl: null
    property var progBridge: null
    property var logBridge: null
    property var formController: null
    property var navigation: null
    property bool prefsMode: false

    AutoLiveDialog {
        id: autoLiveDialog
        runCtrl: root.runCtrl
    }

    readonly property int sideNavIndex: sideNav.currentIndex

    RowLayout {
        anchors.fill: parent
        spacing: 0

        SideNavigationBar {
            id: sideNav
            Layout.fillHeight: true
            visible: !root.prefsMode
            // t() 内部读取 Globals.language，语言切换时本绑定会自动重求值
            model: [
                App.Globals.t("nav.control"),
                App.Globals.t("nav.device"),
                App.Globals.t("nav.config"),
                App.Globals.t("nav.logs"),
                App.Globals.t("nav.about")
            ]

            onCurrentChanging: function(navIndex, previousIndex) {
                if (root.navigation) {
                    root.navigation.requestGuardedAction(App.Globals.t("guard.switch_page"), function() {
                        sideNav.confirmSwitch(navIndex)
                    })
                } else {
                    sideNav.confirmSwitch(navIndex)
                }
            }
        }

        StackLayout {
            id: pageStack
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !root.prefsMode
            currentIndex: sideNav.currentIndex

            ControlPage {
                autoLiveDialog: autoLiveDialog
                runCtrl: root.runCtrl
                progBridge: root.progBridge
            }

            DevicePage {
                tabIndex: index
                formController: root.formController
                runCtrl: root.runCtrl
            }

            SettingsPage {
                formController: root.formController
                runCtrl: root.runCtrl
            }

            LogPage {
                logBridge: root.logBridge
            }

            AboutPage {}
        }
    }
}