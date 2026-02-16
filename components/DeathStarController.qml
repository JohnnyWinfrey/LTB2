// DeathStarController.qml
import QtQuick
import QtQuick.Controls

Rectangle {
    id: deathStarController
    width: 200
    height: 351
    color: "#6f6f6f"
    radius: 5
    border.width: 2
    
    // Property to specify which backend to use
    property string deathStarBackend: "DeathStarBackend"
    
    // Helper function to get the backend object
    function getBackend() {
        if (deathStarBackend === "DeathStar1Backend") {
            return DeathStar1Backend
        } else if (deathStarBackend === "DeathStar2Backend") {
            return DeathStar2Backend
        } else {
            return DeathStarBackend
        }
    }
    
    // Polarizer Position Display
    Rectangle {
        id: polarDisplay
        x: 0
        y: 0
        width: 100
        height: 80
        color: "#4d4d4d"
        border.color: "#000000"
        bottomLeftRadius: 10
        topLeftRadius: 10
        scale: 0.9
        
        Rectangle {
            id: polarValueBg
            x: 8
            y: 5
            width: 84
            height: 37
            color: "#000000"
        }

        Label {
            id: polarValue
            x: 23
            y: 4
            width: 55
            height: 40
            color: "#ff6d00"
            text: getBackend().pPosString
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.pointSize: 20
            font.family: "OCR A"
            scale: 0.9
        }

        Label {
            id: polarLabel
            x: 8
            y: 48
            text: qsTr("Polarizer")
            font.wordSpacing: -0.5
            font.family: "OCR A"
            font.pointSize: 14
        }
    }
    
    // ... (rest of display code same but using getBackend()) ...
    
    // Wave Plate Position Display
    Rectangle {
        id: wavePlateDisplay
        x: 100
        y: 0
        width: 100
        height: 80
        color: "#4d4d4d"
        border.width: 1
        bottomRightRadius: 10
        topRightRadius: 10
        scale: 0.9
        
        Rectangle {
            id: wavePlateValueBg
            x: 8
            y: 5
            width: 84
            height: 37
            color: "#000000"
        }

        Label {
            id: wavePlateValue
            x: 22
            y: 4
            width: 55
            height: 40
            color: "#ff6d00"
            text: getBackend().wPosString
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.family: "OCR A"
            font.pointSize: 21
            scale: 0.9
        }

        Label {
            id: wavePlateLabel
            x: 8
            y: 48
            text: qsTr("λ/4 Plate")
            font.wordSpacing: -0.5
            font.pointSize: 14
            font.family: "OCR A"
        }
    }
    
    // Home Button
    Button {
        id: home
        x: 8
        y: 82
        width: 43
        height: 18
        text: qsTr("Home")
        font.family: "Arial"
        font.pointSize: 7
        onClicked: getBackend().home()
        
        background: Rectangle {
            anchors.fill: parent
            color: "#d600cd"
            radius: 10
        }
    }

    // Polarizer Controls
    Text {
        x: 15
        y: 110
        color: "#bbf6ef"
        text: qsTr("Polarizer")
        font.pixelSize: 14
        font.styleName: "Bold"
        font.family: "Courier"
    }

    Button {
        id: movePolarCW
        x: 135
        y: 132
        width: 55
        height: 40
        text: qsTr("CW ↻")
        font.family: "Arial"
        font.pointSize: 12
        onClicked: getBackend().moveP_CW()
        
        background: Rectangle {
            anchors.fill: parent
            color: "#ff563e"
            border.width: 2
            topRightRadius: 10
            bottomRightRadius: 10
        }
    }

    Button {
        id: movePolarCC
        x: 12
        y: 132
        width: 55
        height: 40
        text: qsTr("↺ CC")
        font.family: "Arial"
        font.pointSize: 12
        onClicked: getBackend().moveP_CC()
        
        background: Rectangle {
            anchors.fill: parent
            color: "#ff563e"
            border.width: 2
            topLeftRadius: 10
            bottomLeftRadius: 10
        }
    }

    // Wave Plate Controls
    Text {
        x: 15
        y: 185
        color: "#bbf6ef"
        text: qsTr("Wave Plate")
        font.pixelSize: 14
        font.styleName: "Bold"
        font.family: "Courier"
    }

    Button {
        id: moveWaveCW
        x: 135
        y: 207
        width: 55
        height: 40
        text: qsTr("CW ↻")
        font.family: "Arial"
        font.pointSize: 12
        onClicked: getBackend().moveW_CW()
        
        background: Rectangle {
            anchors.fill: parent
            color: "#00ffdf"
            border.width: 2
            radius: 10
        }
    }

    Button {
        id: moveWaveCC
        x: 12
        y: 207
        width: 55
        height: 40
        text: qsTr("↺ CC")
        font.family: "Arial"
        font.pointSize: 12
        onClicked: getBackend().moveW_CC()
        
        background: Rectangle {
            anchors.fill: parent
            color: "#00ffdf"
            border.width: 2
            radius: 10
        }
    }
    
    // Position Input (same pattern with getBackend())
    Rectangle {
        id: positionInput
        x: 10
        y: 260
        width: 180
        height: 83
        color: "#4d4d4d"
        border.width: 1
        topLeftRadius: 20
        
        // ... (rest of position input code)
        
        Button {
            id: setPosition
            x: 157
            y: 65
            width: 20
            height: 18
            text: qsTr("Go")
            font.family: "Arial"
            font.pointSize: 6
            onClicked: getBackend().setPosition(polarSetPosition.text, waveSetPosition.text)
            
            background: Rectangle {
                anchors.fill: parent
                color: "#017a03"
                border.width: 2
            }
        }
    }
}