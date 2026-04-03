// DeathStarController.qml
import QtQuick
import QtQuick.Controls

Rectangle {
    id: deathStarController
    width: 200
    height: 200
    color: "#6f6f6f"
    radius: 5
    border.width: 2
    
    property string deathStarBackend: "DeathStarBackend"
    property bool userEditingP: false
    property bool userEditingW: false
    
    function getBackend() {
        if (deathStarBackend === "DeathStar1Backend") {
            return DeathStar1Backend
        } else if (deathStarBackend === "DeathStar2Backend") {
            return DeathStar2Backend
        } else {
            return DeathStarBackend
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 5
        spacing: 8

        // Polarizer and Wave Plate displays side by side
        Row {
            spacing: 0

            // Polarizer Display
            Rectangle {
                width: 95
                height: 80
                color: "#4d4d4d"
                border.color: "#000000"
                topLeftRadius: 10
                bottomLeftRadius: 10

                Column {
                    anchors.fill: parent
                    anchors.margins: 5
                    spacing: 3

                    Label {
                        text: qsTr("Polarizer")
                        font.family: "OCR A"
                        font.pointSize: 10
                        color: "#bbf6ef"
                    }

                    Rectangle {
                        width: 84
                        height: 37
                        color: "#000000"

                        TextInput {
                            id: polarInput
                            anchors.fill: parent
                            text: getBackend().pPosString
                            font.pointSize: 18
                            font.family: "OCR A"
                            color: "#ff6d00"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            onActiveFocusChanged: {
                                userEditingP = activeFocus
                            }
                        }

                        // Update from backend when not editing
                        Connections {
                            target: getBackend()
                            function onPolarRotated() {
                                if (!userEditingP) {
                                    polarInput.text = getBackend().pPosString
                                }
                            }
                        }
                    }
                }
            }

            // Wave Plate Display
            Rectangle {
                width: 95
                height: 80
                color: "#4d4d4d"
                border.color: "#000000"
                topRightRadius: 10
                bottomRightRadius: 10

                Column {
                    anchors.fill: parent
                    anchors.margins: 5
                    spacing: 3

                    Label {
                        text: qsTr("λ/4 Plate")
                        font.family: "OCR A"
                        font.pointSize: 10
                        color: "#bbf6ef"
                    }

                    Rectangle {
                        width: 84
                        height: 37
                        color: "#000000"

                        TextInput {
                            id: wavePlateInput
                            anchors.fill: parent
                            text: getBackend().wPosString
                            font.pointSize: 18
                            font.family: "OCR A"
                            color: "#ff6d00"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            onActiveFocusChanged: {
                                userEditingW = activeFocus
                            }
                        }

                        Connections {
                            target: getBackend()
                            function onWavePlateRotated() {
                                if (!userEditingW) {
                                    wavePlateInput.text = getBackend().wPosString
                                }
                            }
                        }
                    }
                }
            }
        }

        // Set and Home buttons
        Row {
            spacing: 10
            anchors.horizontalCenter: parent.horizontalCenter

            Button {
                width: 80
                height: 28
                text: qsTr("Set")
                font.family: "Arial"
                font.pointSize: 9
                onClicked: {
                    getBackend().setPosition(polarInput.text, wavePlateInput.text)
                    polarInput.focus = false
                    wavePlateInput.focus = false
                }

                background: Rectangle {
                    anchors.fill: parent
                    color: "#017a03"
                    border.width: 2
                    radius: 10
                }
            }

            Button {
                width: 80
                height: 28
                text: qsTr("Home")
                font.family: "Arial"
                font.pointSize: 9
                onClicked: getBackend().home()

                background: Rectangle {
                    anchors.fill: parent
                    color: "#d600cd"
                    border.width: 2
                    radius: 10
                }
            }
        }
    }
}