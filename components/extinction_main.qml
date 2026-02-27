// extinction_main.qml
import QtQuick
import QtQuick.Controls

Rectangle {
    anchors.fill: parent
    color: "#6f6f6f"
    
    Row {
        anchors.fill: parent
        spacing: 0
        
        Loader {
            width: 200
            height: 900
            source: "XWingController.qml"
        }
        
        Column {
            width: 400
            height: 900
            spacing: 0
            
            Loader {
                width: 400
                height: 300
                source: "CornerstoneController.qml"
            }
            
            Loader {
                width: 400
                height: 350
                source: "PositionManager.qml"
            }
            
            Rectangle {
                width: 400
                height: 50
                color: "#313131"
                border.width: 3
                
                Row {
                    anchors.centerIn: parent
                    spacing: 10
                    
                    Button {
                        width: 90
                        height: 30
                        text: "← Home"
                        onClicked: App.home()
                        
                        background: Rectangle {
                            anchors.fill: parent
                            color: "#676767"
                            border.width: 2
                            radius: 5
                        }
                        
                        contentItem: Text {
                            text: parent.text
                            font.pixelSize: 10
                            font.family: "Courier"
                            color: "#ffffff"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    
                    Button {
                        width: 130
                        height: 30
                        text: "Start Extinction"
                        onClicked: ExtinctionBackend.threading()
                        
                        background: Rectangle {
                            anchors.fill: parent
                            color: "#149700"
                            border.width: 2
                            radius: 5
                        }
                        
                        contentItem: Text {
                            text: parent.text
                            font.pixelSize: 10
                            font.family: "Courier"
                            color: "#ffffff"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    
                    Button {
                        width: 90
                        height: 30
                        text: "Stop"
                        onClicked: ExtinctionBackend.stopScan()
                        
                        background: Rectangle {
                            anchors.fill: parent
                            color: "#d80000"
                            border.width: 2
                            radius: 5
                        }
                        
                        contentItem: Text {
                            text: parent.text
                            font.pixelSize: 10
                            font.family: "Courier"
                            color: "#ffffff"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
        }
    }
}