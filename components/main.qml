import QtQuick 2.15
import QtQuick.Controls 2.15

ApplicationWindow {
    visible: true
    width: 600
    height: 600
    title: "Hyperspectral"
    
    Row {
        anchors.fill: parent
        spacing: 0
        
        Column {
            width: 200
            height: 550
            spacing: 0
            
            Loader {
                width: 200
                height: 350
                source: "XWingController.qml"
            }
        }
        
        Column {
            width: 400
            height: 550
            spacing: 0
            
            Loader {
                width: 400
                height: 300
                source: "CornerstoneController.qml"
            }
            
            Loader {
                width: 400
                height: 250
                source: "PositionManager.qml"
            }
            
            // Automation controls
            Rectangle {
                width: 400
                height: 50
                color: "#313131"
                border.width: 3
                
                Rectangle {
                    x: 8
                    y: 8
                    width: 384
                    height: 34
                    color: "#676767"
                    radius: 5
                    border.width: 2
                    
                    Rectangle {
                        x: 10
                        y: 8
                        width: 180
                        height: 18
                        color: "#149700"
                        border.width: 2
                        
                        Button {
                            anchors.fill: parent
                            text: "Start Scan"
                            font.pixelSize: 9
                            onClicked: AutomationBackend.threading()
                        }
                    }
                    
                    Rectangle {
                        x: 194
                        y: 8
                        width: 180
                        height: 18
                        color: "#d80000"
                        border.width: 2
                        
                        Button {
                            anchors.fill: parent
                            text: "Stop Scan"
                            font.pixelSize: 9
                            onClicked: AutomationBackend.stopScan()
                        }
                    }
                }
            }
        }
    }
}