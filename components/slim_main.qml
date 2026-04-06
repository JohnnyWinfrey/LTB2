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
            
            // Left DeathStar - PSG
            Column {
                width: 200
                height: 800
                spacing: 10
                
                Text {
                    width: 200
                    height: 30
                    text: "State Generator"
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
                    height: 200
                    source: "DeathStarController.qml"
                    
                    onLoaded: {
                        // This loader uses PSG_Backend
                        item.deathStarBackend = "PSG_Backend"
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
                    height: 600
                    color: "#313131"
                    border.width: 3
                    
                    Rectangle {
                        x: 8
                        y: 8
                        width: 184
                        height: 584
                        color: "#676767"
                        radius: 10
                        border.width: 3
                        
                        Column {
                            anchors.centerIn: parent
                            spacing: 12
                            
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "SLIM Controls"
                                font.pixelSize: 18
                                font.family: "Courier"
                                color: "#bbf6ef"
                            }
                            
                            // --- Scan Mode Buttons ---
                            Button {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 150
                                height: 35
                                text: "Background"
                                onClicked: SLIMBackend.threading("calibration")
                                
                                background: Rectangle {
                                    anchors.fill: parent
                                    color: "#149700"
                                    border.width: 2
                                }
                            }
                            
                            Rectangle {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 150
                                height: 25
                                color: "#000000"
                                border.width: 1
                                radius: 4

                                Text {
                                    anchors.centerIn: parent
                                    text: "BG: " + SpectroBackend.bgCounts
                                    font.pixelSize: 12
                                    font.family: "OCR A"
                                    color: "#ff6d00"
                                }
                            }

                            Button {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 150
                                height: 35
                                text: "Mueller"
                                onClicked: SLIMBackend.threading("mueller")
                                
                                background: Rectangle {
                                    anchors.fill: parent
                                    color: "#149700"
                                    border.width: 2
                                }
                            }
                            
                            
                            Button {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 150
                                height: 35
                                text: "Stokes"
                                onClicked: SLIMBackend.threading("stokes")
                                
                                background: Rectangle {
                                    anchors.fill: parent
                                    color: "#149700"
                                    border.width: 2
                                }
                            }
                            
                            Button {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 150
                                height: 35
                                text: "Planar Diffraction"
                                onClicked: SLIMBackend.threading("edgeLP")
                                
                                background: Rectangle {
                                    anchors.fill: parent
                                    color: "#0a7a9e"
                                    border.width: 2
                                }
                            }
                            
                            Button {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 150
                                height: 35
                                text: "Circular Polar."
                                onClicked: SLIMBackend.threading("edgeCP")
                                
                                background: Rectangle {
                                    anchors.fill: parent
                                    color: "#0a7a9e"
                                    border.width: 2
                                }
                            }
                            
                            // --- Stop Button ---
                            
                            Button {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 150
                                height: 35
                                text: "Stop"
                                onClicked: SLIMBackend.stopScan()
                                
                                background: Rectangle {
                                    anchors.fill: parent
                                    color: "#d80000"
                                    border.width: 2
                                }
                            }
                        }
                    }
                }
                Loader {
                    width: 200
                    height: 200
                    source: "ScanSettings.qml"
                }
            }
            
            // Right DeathStar - PSA
            Column {
                width: 200
                height: 800
                spacing: 10
                
                Text {
                    width: 200
                    height: 30
                    text: "State Analyzer"
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
                    height: 200
                    source: "DeathStarController.qml"
                    
                    onLoaded: {
                        // This loader uses PSA_Backend
                        item.deathStarBackend = "PSA_Backend"
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