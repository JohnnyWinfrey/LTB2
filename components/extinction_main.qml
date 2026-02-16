// extinction_main.qml
import QtQuick
import QtQuick.Controls

ApplicationWindow {
    visible: true
    width: 600
    height: 900
    title: "Extinction"
    
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
                        width: 180
                        height: 30
                        text: "Start Extinction"
                        onClicked: ExtinctionBackend.threading()
                        
                        background: Rectangle {
                            anchors.fill: parent
                            color: "#149700"
                            border.width: 2
                        }
                    }
                    
                    Button {
                        width: 180
                        height: 30
                        text: "Stop"
                        onClicked: ExtinctionBackend.stopScan()
                        
                        background: Rectangle {
                            anchors.fill: parent
                            color: "#d80000"
                            border.width: 2
                        }
                    }
                }
            }
        }
    }
}