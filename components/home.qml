// home.qml
import QtQuick
import QtQuick.Controls

ApplicationWindow {
    visible: true
    width: 600
    height: 400
    title: "Hyperspectral System"
    
    Rectangle {
        anchors.fill: parent
        color: "#2d2d2d"
        
        Column {
            anchors.centerIn: parent
            spacing: 30
            
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Select Automation"
                font.pixelSize: 32
                font.family: "Courier"
                color: "#bbf6ef"
            }
            
            Button {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 300
                height: 60
                text: "Extinction"
                onClicked: AppBackend.loadAutomation("extinction")
                
                background: Rectangle {
                    anchors.fill: parent
                    color: "#149700"
                    border.width: 3
                    radius: 10
                }
                
                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 18
                    font.family: "Courier"
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
            
            Button {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 300
                height: 60
                text: "Single Fluor"
                onClicked: AppBackend.loadAutomation("singlefluor")
                
                background: Rectangle {
                    anchors.fill: parent
                    color: "#2196F3"
                    border.width: 3
                    radius: 10
                }
                
                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 18
                    font.family: "Courier"
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
            
            Button {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 300
                height: 60
                text: "SLIM"
                onClicked: AppBackend.loadAutomation("slim")
                
                background: Rectangle {
                    anchors.fill: parent
                    color: "#ff6d00"
                    border.width: 3
                    radius: 10
                }
                
                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 18
                    font.family: "Courier"
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
}