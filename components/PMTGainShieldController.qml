import QtQuick
import QtQuick.Controls

Rectangle {
    id: pmtgainshieldController
    width: 150
    height: 100
    color: "#6f6f6f"
    radius: 5
    border.width: 2

    TextInput {
        id: desiredGain
        x: 20
        y: 20
        width: 55
        height: 40
        color: "#ff6d00"
        text: qsTr("0.000")
        font.pixelSize: 17
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.family: "Cascadia Mono"
    }

    Button {
        id: updateGain
        x: 75
        y: 86
        width: 55
        height: 40
        text: qsTr("Update")
        font.family: "Consolas"
        icon.color: "#b23a3a"
        onClicked: PMTGainShieldBackend.changeGain(desiredGain.text)
        background: Rectangle {
            id: rectangle10
            x: 0
            y: 0
            width: 55
            height: 40
            color: "#00ffdf"
            border.width: 2
            topRightRadius: 10
            topLeftRadius: 10
        }
    }

}
