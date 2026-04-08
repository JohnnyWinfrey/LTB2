// XWingScanSettings.qml
// Sample name save, grid configuration, and scan progress/status display.
import QtQuick
import QtQuick.Controls

Rectangle {
    width: 400
    height: 200
    color: "#313131"
    border.width: 3

    Rectangle {
        x: 8; y: 8
        width: 384; height: 184
        color: "#676767"
        radius: 10
        border.width: 3

        Column {
            anchors.centerIn: parent
            spacing: 14

            // Sample name + Save button
            Row {
                spacing: 8
                anchors.horizontalCenter: parent.horizontalCenter

                Text {
                    text: "Sample:"
                    font.pixelSize: 12; font.family: "Courier"; color: "#ffffff"
                    verticalAlignment: Text.AlignVCenter; height: 28
                }

                Rectangle {
                    width: 185; height: 28; color: "#000000"; border.width: 1

                    TextInput {
                        id: sampleNameInput
                        anchors.fill: parent; anchors.margins: 3
                        text: "sample"
                        font.pixelSize: 13; font.family: "Cascadia Mono"; color: "#ff6d00"
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Button {
                    width: 55; height: 28
                    text: "Save"
                    onClicked: XWingScanBackend.setSampleName(sampleNameInput.text)

                    background: Rectangle {
                        anchors.fill: parent; color: "#0a7a9e"; border.width: 2; radius: 4
                    }
                    contentItem: Text {
                        text: parent.text; font.pixelSize: 11; font.family: "Courier"; color: "#ffffff"
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            // Grid config: Nx, Ny, Step
            Row {
                spacing: 14
                anchors.horizontalCenter: parent.horizontalCenter

                Row {
                    spacing: 6
                    Text { text: "Nx:"; font.pixelSize: 12; font.family: "Courier"; color: "#ffffff"; verticalAlignment: Text.AlignVCenter; height: 26 }
                    Rectangle {
                        width: 50; height: 26; color: "#000000"; border.width: 1
                        TextInput {
                            id: nxInput
                            anchors.fill: parent; anchors.margins: 3
                            text: "5"; font.pixelSize: 13; font.family: "Cascadia Mono"; color: "#ff6d00"
                            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                            onEditingFinished: XWingScanBackend.setNx(text)
                        }
                    }
                }

                Row {
                    spacing: 6
                    Text { text: "Ny:"; font.pixelSize: 12; font.family: "Courier"; color: "#ffffff"; verticalAlignment: Text.AlignVCenter; height: 26 }
                    Rectangle {
                        width: 50; height: 26; color: "#000000"; border.width: 1
                        TextInput {
                            id: nyInput
                            anchors.fill: parent; anchors.margins: 3
                            text: "5"; font.pixelSize: 13; font.family: "Cascadia Mono"; color: "#ff6d00"
                            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                            onEditingFinished: XWingScanBackend.setNy(text)
                        }
                    }
                }

                Row {
                    spacing: 6
                    Text { text: "Step(mm):"; font.pixelSize: 12; font.family: "Courier"; color: "#ffffff"; verticalAlignment: Text.AlignVCenter; height: 26 }
                    Rectangle {
                        width: 60; height: 26; color: "#000000"; border.width: 1
                        TextInput {
                            id: spacingInput
                            anchors.fill: parent; anchors.margins: 3
                            text: "0.5"; font.pixelSize: 13; font.family: "Cascadia Mono"; color: "#ff6d00"
                            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                            onEditingFinished: XWingScanBackend.setSpacing(text)
                        }
                    }
                }
            }

            // Progress + Status
            Column {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 4

                Text {
                    id: progressText
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "—"
                    font.pixelSize: 18; font.family: "Cascadia Mono"; color: "#ff6d00"
                }

                Text {
                    id: statusText
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Ready"
                    font.pixelSize: 12; font.family: "Courier"; color: "#43ac33"
                }
            }
        }
    }

    Connections {
        target: XWingScanBackend
        function onProgressChanged(msg) { progressText.text = msg }
        function onStatusChanged(msg)   { statusText.text   = msg }
    }
}
