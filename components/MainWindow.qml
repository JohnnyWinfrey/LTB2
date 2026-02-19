import QtQuick
import QtQuick.Controls

ApplicationWindow {
    visible: true
    width: 600
    height: 900
    title: "LTB2"
    
    Loader {
        id: pageLoader
        anchors.fill: parent
        source: "HomePage.qml"
    }
    
    Connections {
        target: App
        function onPageChanged(page) {
            pageLoader.source = page
        }
    }
}