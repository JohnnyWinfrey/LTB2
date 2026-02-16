// slim_main.qml
import QtQuick
import QtQuick.Controls

ApplicationWindow {
    visible: true
    width: 600
    height: 900
    title: "SLIM Automation"
    
    Column {
        anchors.fill: parent
        spacing: 0
        
        // Title bar with back button
        Rectangle {
            width: 600
            height: 50
            color: "#313131"
            border.width: 3
            
            Row {
                anchors.centerIn: parent
                spacing: 200
                
                Button {
                    width: 80
                    height: 30
                    text: "← Home"
                    onClicked: {
                        // Go back to home - will need to reload home.qml
                        Qt.quit()  // For now, just close
                    }
                    
                    background: Rectangle {
                        anchors.fill: parent
                        color: "#676767"
                        border.width: 2
                    }
                }
                
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "SLIM - Structured Illumination"
                    font.pixelSize: 20
                    font.family: "Courier"
                    color: "#bbf6ef"
                }
            }
        }
        
        // Main content area
        Row {
            width: 600
            height: 800
            spacing: 0
            
            // Left DeathStar - Illumination
            Column {
                width: 200
                height: 800
                spacing: 10
                
                Text {
                    width: 200
                    height: 30
                    text: "Illumination"
                    font.pixelSize: 16
                    font.family: "Courier"
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    
                    Rectangle {
                        anchors.fill: parent
                        color: "#2d2d2d"
                        z: -1
                    }
                }
                
                Loader {
                    width: 200
                    height: 351
                    source: "DeathStarController.qml"
                    
                    onLoaded: {
                        // This loader uses DeathStar1Backend
                        item.deathStarBackend = "DeathStar1Backend"
                    }
                }
            }
            
            // Middle - Control Panel
            Column {
                width: 200
                height: 800
                spacing: 0
                
                Rectangle {
                    width: 200
                    height: 400
                    color: "#313131"
                    border.width: 3
                    
                    Rectangle {
                        x: 8
                        y: 8
                        width: 184
                        height: 384
                        color: "#676767"
                        radius: 10
                        border.width: 3
                        
                        Column {
                            anchors.centerIn: parent
                            spacing: 20
                            
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "SLIM Controls"
                                font.pixelSize: 18
                                font.family: "Courier"
                                color: "#bbf6ef"
                            }
                            
                            Button {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 150
                                height: 40
                                text: "Start SLIM"
                                onClicked: SLIMBackend.threading()
                                
                                background: Rectangle {
                                    anchors.fill: parent
                                    color: "#149700"
                                    border.width: 2
                                }
                            }
                            
                            Button {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 150
                                height: 40
                                text: "Stop"
                                // onClicked: SLIMBackend.stopScan()
                                
                                background: Rectangle {
                                    anchors.fill: parent
                                    color: "#d80000"
                                    border.width: 2
                                }
                            }
                            
                            Rectangle {
                                width: 150
                                height: 2
                                color: "#4d4d4d"
                            }
                            
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "Scan Parameters"
                                font.pixelSize: 14
                                font.family: "Courier"
                                color: "#b9f4ed"
                            }
                            
                            Column {
                                anchors.horizontalCenter: parent.horizontalCenter
                                spacing: 10
                                
                                Row {
                                    spacing: 10
                                    
                                    Text {
                                        width: 80
                                        text: "# Angles:"
                                        font.pixelSize: 11
                                        font.family: "Courier"
                                        color: "#ffffff"
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                    
                                    Rectangle {
                                        width: 50
                                        height: 20
                                        color: "#000000"
                                        border.width: 1
                                        
                                        TextInput {
                                            id: numAngles
                                            anchors.fill: parent
                                            text: "5"
                                            font.pixelSize: 12
                                            color: "#ff6d00"
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                        }
                                    }
                                }
                                
                                Row {
                                    spacing: 10
                                    
                                    Text {
                                        width: 80
                                        text: "# Phases:"
                                        font.pixelSize: 11
                                        font.family: "Courier"
                                        color: "#ffffff"
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                    
                                    Rectangle {
                                        width: 50
                                        height: 20
                                        color: "#000000"
                                        border.width: 1
                                        
                                        TextInput {
                                            id: numPhases
                                            anchors.fill: parent
                                            text: "3"
                                            font.pixelSize: 12
                                            color: "#ff6d00"
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            // Right DeathStar - Detection
            Column {
                width: 200
                height: 800
                spacing: 10
                
                Text {
                    width: 200
                    height: 30
                    text: "Detection"
                    font.pixelSize: 16
                    font.family: "Courier"
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    
                    Rectangle {
                        anchors.fill: parent
                        color: "#2d2d2d"
                        z: -1
                    }
                }
                
                Loader {
                    width: 200
                    height: 351
                    source: "DeathStarController.qml"
                    
                    onLoaded: {
                        // This loader uses DeathStar2Backend
                        item.deathStarBackend = "DeathStar2Backend"
                    }
                }
            }
        }
        
        // Status bar
        Rectangle {
            width: 600
            height: 50
            color: "#2d2d2d"
            border.width: 2
            
            Text {
                anchors.centerIn: parent
                text: "Ready"
                font.pixelSize: 14
                font.family: "Courier"
                color: "#43ac33"
            }
        }
    }
}