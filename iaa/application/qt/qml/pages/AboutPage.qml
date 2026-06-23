import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".." as App
import "../components"

// import Iaa.Controllers 1.0

PageContainer {
    title: App.Globals.t("nav.about")
    
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 16

        Image {
            source: App.Globals.assetPath("marry_with_6_mikus.png")
            Layout.preferredWidth: 220
            Layout.preferredHeight: 220
            fillMode: Image.PreserveAspectFit
            HoverHandler {
                id: hoverHandler
            }
        }

        Label {
            text: App.Globals.t("about.tagline")
            opacity: hoverHandler.hovered ? 1 : 0
            font.pixelSize: 10
            font.weight: Font.Light
            color: '#000000'
            Layout.alignment: Qt.AlignHCenter

            Behavior on opacity {
                NumberAnimation { duration: 200 }
            }
        }

        Label {
            text: "一歌小助手 iaa"
            font.pixelSize: 28
            Layout.alignment: Qt.AlignHCenter
        }
        Label {
            text: App.Globals.t("about.version").replace("{version}", appController.version)
            Layout.alignment: Qt.AlignHCenter
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Link { label: "GitHub"; href: "https://github.com/XcantloadX/ichikas-auto-assistant" }
            Link { label: "Bilibili"; href: "https://space.bilibili.com/3546853903698457" }
            Link { label: App.Globals.t("about.docs"); href: "https://p.kdocs.cn/s/AGBH56RBAAAFS" }
            Link { label: App.Globals.t("about.qq_group"); href: "https://qm.qq.com/q/Mu1SSfK1Gg" }
        }
    }
}
