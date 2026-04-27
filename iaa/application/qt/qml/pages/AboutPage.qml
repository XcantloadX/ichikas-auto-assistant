import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".." as App
import "../components"

// import Iaa.Controllers 1.0

PageContainer {
    title: "关于"
    
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 16

        Image {
            source: App.Globals.assetPath("marry_with_6_mikus.png")
            width: 160
            height: 160
            fillMode: Image.PreserveAspectFit
            HoverHandler {
                id: hoverHandler
            }
        }

        Label {
            text: "我同时和六个初音未来结婚"
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
            text: "版本 v" + appController.version
            Layout.alignment: Qt.AlignHCenter
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Link { label: "GitHub"; href: "https://github.com/XcantloadX/ichikas-auto-assistant" }
            Link { label: "Bilibili"; href: "https://space.bilibili.com/3546853903698457" }
            Link { label: "教程文档"; href: "https://p.kdocs.cn/s/AGBH56RBAAAFS" }
            Link { label: "QQ 群"; href: "https://qm.qq.com/q/Mu1SSfK1Gg" }
        }
    }
}
