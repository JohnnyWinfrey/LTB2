import QtQuick
import QtQuick.Controls

Rectangle {
    color: "#2d2d2d"
    
    Column {
        anchors.centerIn: parent
        spacing: 30
        
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Select Automation"
            font.pixelSize: 32
            color: "#bbf6ef"
        }
        
        Button {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 300
            height: 60
            text: "Extinction"
            onClicked: App.load("extinction")
        }
        
        Button {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 300
            height: 60
            text: "Single Fluor"
            onClicked: App.load("singlefluor")
        }
        
        Button {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 300
            height: 60
            text: "SLIM"
            onClicked: App.load("slim")
        }
    }
}