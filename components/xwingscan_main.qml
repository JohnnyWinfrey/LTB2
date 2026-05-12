// xwingscan_main.qml
import QtQuick
import QtQuick.Controls

Rectangle {
    anchors.fill: parent
    color: "#6f6f6f"

    Row {
        anchors.fill: parent
        spacing: 0

        // Left column: jog controls + detector selector
        Column {
            width: 200
            height: parent.height
            spacing: 0

            Loader {
                width: 200
                height: 240
                source: "XWingSimpleController.qml"
            }

            // Detector selector panel
            Rectangle {
                width: 200
                height: 160
                color: "#313131"
                border.width: 3

                Rectangle {
                    x: 8; y: 8
                    width: 184; height: 144
                    color: "#676767"
                    radius: 10
                    border.width: 3

                    Column {
                        anchors.centerIn: parent
                        spacing: 10

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Detector"
                            font.pixelSize: 14
                            font.family: "Courier"
                            color: "#bbf6ef"
                        }

                        ComboBox {
                            id: detectorCombo
                            width: 160
                            model: ["PMT", "Spectrometer", "Camera"]
                            font.family: "Courier"
                            font.pixelSize: 11

                            onActivated: {
                                var types = ["pmt", "spectrometer", "camera"]
                                XWingScanBackend.setDetectorType(types[currentIndex])
                            }

                            background: Rectangle {
                                color: "#4d4d4d"
                                border.width: 2
                                radius: 4
                            }
                            contentItem: Text {
                                leftPadding: 8
                                text: detectorCombo.displayText
                                font: detectorCombo.font
                                color: "#ff6d00"
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        Button {
                            width: 160; height: 30
                            text: "Detector Settings"
                            onClicked: detectorSettingsPopup.visible = true

                            background: Rectangle {
                                anchors.fill: parent
                                color: "#00579e"
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

        // Right column: wavelength controls + scan settings + buttons
        Column {
            width: 400
            height: parent.height
            spacing: 0

            Loader {
                width: 400
                height: 300
                source: "CornerstoneController.qml"
            }

            Loader {
                width: 400
                height: 200
                source: "XWingScanSettings.qml"
            }

            // Start / Stop / Home buttons
            Rectangle {
                width: 400
                height: 60
                color: "#313131"
                border.width: 3

                Row {
                    anchors.centerIn: parent
                    spacing: 10

                    Button {
                        width: 80; height: 32
                        text: "← Home"
                        onClicked: App.home()

                        background: Rectangle {
                            anchors.fill: parent; color: "#676767"; border.width: 2; radius: 5
                        }
                        contentItem: Text {
                            text: parent.text; font.pixelSize: 10; font.family: "Courier"; color: "#ffffff"
                            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                        }
                    }

                    Button {
                        width: 155; height: 32
                        text: "Start Scan"
                        onClicked: XWingScanBackend.threading()

                        background: Rectangle {
                            anchors.fill: parent; color: "#149700"; border.width: 2; radius: 5
                        }
                        contentItem: Text {
                            text: parent.text; font.pixelSize: 11; font.family: "Courier"; color: "#ffffff"
                            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                        }
                    }

                    Button {
                        width: 80; height: 32
                        text: "Stop"
                        onClicked: XWingScanBackend.stopScan()

                        background: Rectangle {
                            anchors.fill: parent; color: "#d80000"; border.width: 2; radius: 5
                        }
                        contentItem: Text {
                            text: parent.text; font.pixelSize: 11; font.family: "Courier"; color: "#ffffff"
                            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }

            // Camera popup button + filler
            Rectangle {
                width: 400
                height: parent.height - 560
                color: "#6f6f6f"

                Button {
                    x: 10
                    y: 8
                    width: 120
                    height: 28
                    text: "Camera View"
                    onClicked: cameraPopup.visible = true

                    background: Rectangle {
                        anchors.fill: parent; color: "#00579e"; border.width: 2; radius: 5
                    }
                    contentItem: Text {
                        text: parent.text; font.pixelSize: 10; font.family: "Courier"; color: "#ffffff"
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }

    CameraViewPopup {
        id: cameraPopup
        visible: false
    }

    DetectorSettingsPopup {
        id: detectorSettingsPopup
        visible: false
        detectorType: XWingScanBackend.detectorType
    }
}
