// ScanSettings.qml
import QtQuick
import QtQuick.Controls

Rectangle {
    id: scanSettings
    width: 200
    height: 200
    color: "#313131"
    border.width: 3

    Rectangle {
        x: 8
        y: 8
        width: 184
        height: 184
        color: "#676767"
        radius: 10
        border.width: 3

        Column {
            anchors.centerIn: parent
            spacing: 8

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Scan Settings"
                font.pixelSize: 14
                font.family: "Courier"
                color: "#bbf6ef"
            }

            // Sample Name
            Row {
                spacing: 5
                Text { width: 55; text: "Name:"; font.pixelSize: 10; font.family: "Courier"; color: "#ffffff"; verticalAlignment: Text.AlignVCenter }
                Rectangle {
                    width: 100; height: 18; color: "#000000"; border.width: 1
                    TextInput {
                        id: sampleNameInput
                        anchors.fill: parent
                        text: "sample"
                        font.pixelSize: 11; color: "#ff6d00"
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                        onTextChanged: SpectroBackend.setSampleName(text)
                    }
                }
            }

            // X and Y
            Row {
                spacing: 5
                Text { width: 55; text: "X:"; font.pixelSize: 10; font.family: "Courier"; color: "#ffffff"; verticalAlignment: Text.AlignVCenter }
                Rectangle {
                    width: 40; height: 18; color: "#000000"; border.width: 1
                    TextInput {
                        id: scanXInput
                        anchors.fill: parent; text: "0"
                        font.pixelSize: 11; color: "#ff6d00"
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                        onTextChanged: SpectroBackend.setScanX(text)
                    }
                }
                Text { width: 15; text: "Y:"; font.pixelSize: 10; font.family: "Courier"; color: "#ffffff"; verticalAlignment: Text.AlignVCenter }
                Rectangle {
                    width: 40; height: 18; color: "#000000"; border.width: 1
                    TextInput {
                        id: scanYInput
                        anchors.fill: parent; text: "0"
                        font.pixelSize: 11; color: "#ff6d00"
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                        onTextChanged: SpectroBackend.setScanY(text)
                    }
                }
            }

            // Side and Region
            Row {
                spacing: 5
                Text { width: 55; text: "Side:"; font.pixelSize: 10; font.family: "Courier"; color: "#ffffff"; verticalAlignment: Text.AlignVCenter }
                Rectangle {
                    width: 40; height: 18; color: "#000000"; border.width: 1
                    TextInput {
                        id: sideInput
                        anchors.fill: parent; text: "x"
                        font.pixelSize: 11; color: "#ff6d00"
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                        onTextChanged: SpectroBackend.setSide(text)
                    }
                }
                Text { width: 15; text: "R:"; font.pixelSize: 10; font.family: "Courier"; color: "#ffffff"; verticalAlignment: Text.AlignVCenter }
                Rectangle {
                    width: 40; height: 18; color: "#000000"; border.width: 1
                    TextInput {
                        id: regionInput
                        anchors.fill: parent; text: "1"
                        font.pixelSize: 11; color: "#ff6d00"
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                        onTextChanged: SpectroBackend.setRegion(text)
                    }
                }
            }

            // Integration Time
            Row {
                spacing: 5
                Text { width: 55; text: "Int(μs):"; font.pixelSize: 10; font.family: "Courier"; color: "#ffffff"; verticalAlignment: Text.AlignVCenter }
                Rectangle {
                    width: 100; height: 18; color: "#000000"; border.width: 1
                    TextInput {
                        id: intTimeInput
                        anchors.fill: parent; text: "500000"
                        font.pixelSize: 11; color: "#ff6d00"
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                        onTextChanged: SpectroBackend.setIntegration(text)
                    }
                }
            }
        }
    }
}