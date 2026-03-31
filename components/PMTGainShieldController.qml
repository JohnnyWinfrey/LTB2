import QtQuick
import QtQuick.Controls

Rectangle {
    id: pmtGainShieldController
    width: 200
    height: 200
    color: "#6f6f6f"
    radius: 5
    border.width: 2

    Rectangle {
        id: background
        x: 8
        y: 8
        width: 184
        height: 184
        color: "#676767"
        radius: 10
        border.width: 3

        Text {
            id: title
            x: 25
            y: 10
            color: "#bbf6ef"
            text: qsTr("PMT Gain Shield")
            font.pixelSize: 16
            font.styleName: "Bold"
            font.family: "Courier"
        }

        // Current Gain Display
        Rectangle {
            id: gainDisplay
            x: 15
            y: 40
            width: 154
            height: 60
            color: "#4d4d4d"
            radius: 5
            border.width: 2
            border.color: "#000000"

            Text {
                x: 10
                y: 5
                color: "#b9f4ed"
                text: qsTr("Current Gain")
                font.pixelSize: 12
                font.styleName: "Bold"
                font.family: "Courier"
            }

            Rectangle {
                x: 10
                y: 25
                width: 134
                height: 25
                color: "#000000"
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    color: "#ff6d00"
                    text: PMTGainShieldBackend.gain.toFixed(3)
                    font.pixelSize: 18
                    font.family: "OCR A"
                }
            }
        }

        // Set Gain Section
        Text {
            x: 15
            y: 110
            color: "#b9f4ed"
            text: qsTr("Set Gain")
            font.pixelSize: 12
            font.styleName: "Bold"
            font.family: "Courier"
        }

        Rectangle {
            id: gainInputBackground
            x: 15
            y: 130
            width: 100
            height: 25
            color: "#000000"
            border.width: 2

            TextInput {
                id: gainInput
                anchors.fill: parent
                anchors.margins: 3
                color: "#ff6d00"
                text: "0.000"
                font.pixelSize: 14
                font.family: "OCR A"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        Rectangle {
            id: setGainButton
            x: 120
            y: 130
            width: 49
            height: 25
            color: "#149700"
            border.width: 2
            radius: 5

            Button {
                id: setGain
                anchors.fill: parent
                text: qsTr("Set")
                font.family: "Arial"
                font.pointSize: 8
                onClicked: PMTGainShieldBackend.changeGain(gainInput.text)

                background: Rectangle {
                    anchors.fill: parent
                    color: "transparent"
                }

                contentItem: Text {
                    text: parent.text
                    font: parent.font
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
}