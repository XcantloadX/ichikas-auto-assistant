import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

PageContainer {
    id: root
    title: "帮助"
    showTitle: false

    property var topics: []
    property int currentTopicIndex: -1

    function loadTopics() {
        var data = JSON.parse(helpController.topicsJson())
        root.topics = data
        if (data.length > 0) {
            root.currentTopicIndex = 0
        }
    }

    function loadContent(topicId) {
        var html = helpController.contentHtml(topicId)
        contentEdit.text = html
    }

    Component.onCompleted: {
        loadTopics()
    }

    RowLayout {
        anchors.fill: parent
        spacing: 1

        Rectangle {
            Layout.preferredWidth: 200
            Layout.fillHeight: true
            color: "transparent"

            ListView {
                id: topicList
                anchors.fill: parent
                anchors.margins: 8
                model: root.topics
                spacing: 2
                clip: true

                delegate: ItemDelegate {
                    width: ListView.view.width
                    height: 36
                    text: modelData.title
                    highlighted: root.currentTopicIndex === index
                    onClicked: {
                        root.currentTopicIndex = index
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"

            ScrollView {
                anchors.fill: parent
                anchors.margins: 16
                clip: true

                TextEdit {
                    id: contentEdit
                    width: parent.width
                    readOnly: true
                    textFormat: TextEdit.RichText
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    font.pixelSize: 14
                    onLinkActivated: function(link) {
                        Qt.openUrlExternally(link)
                    }
                }
            }
        }
    }

    onCurrentTopicIndexChanged: {
        if (root.currentTopicIndex >= 0 && root.currentTopicIndex < root.topics.length) {
            var topic = root.topics[root.currentTopicIndex]
            root.loadContent(topic.id)
        }
    }
}
