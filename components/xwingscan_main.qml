// xwingscan_main.qml
import QtQuick
import QtQuick.Controls

Rectangle {
    anchors.fill: parent
    color: "#6f6f6f"

    Row {
        anchors.fill: parent
        spacing: 0

        // Left column: jog controls + PMT gain
        Column {
            width: 200
            height: parent.height
            spacing: 0

            Loader {
                width: 200
                height: 240
                source: "XWingSimpleController.qml"
            }

            Loader {
                width: 200
                height: 200
                source: "PMTGainShieldController.qml"
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

            // Filler
            Rectangle {
                width: 400
                height: parent.height - 560
                color: "#6f6f6f"
            }
        }
    }
}
