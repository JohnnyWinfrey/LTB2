// xwingscan_main.qml
import QtQuick
import QtQuick.Controls

Rectangle {
    anchors.fill: parent
    color: "#6f6f6f"

    Row {
        anchors.fill: parent
        spacing: 0

        // Left: XWing jog controller
        Loader {
            width: 200
            height: 900
            source: "XWingController.qml"
        }

        // Right: Scan control panel
        Column {
            width: 400
            height: 900
            spacing: 0

            // Panel A – Title + Home button
            Rectangle {
                width: 400
                height: 50
                color: "#313131"
                border.width: 3

                Row {
                    anchors.centerIn: parent
                    spacing: 120

                    Button {
                        width: 80
                        height: 30
                        text: "← Home"
                        onClicked: App.home()

                        background: Rectangle {
                            anchors.fill: parent
                            color: "#676767"
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

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "XWing Spatial Scan"
                        font.pixelSize: 18
                        font.family: "Courier"
                        color: "#bbf6ef"
                    }
                }
            }

            // Panel B – Scan configuration inputs
            Rectangle {
                width: 400
                height: 200
                color: "#313131"
                border.width: 3

                Rectangle {
                    x: 8
                    y: 8
                    width: 384
                    height: 184
                    color: "#676767"
                    radius: 10
                    border.width: 3

                    Column {
                        anchors.centerIn: parent
                        spacing: 12

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Scan Configuration"
                            font.pixelSize: 14
                            font.family: "Courier"
                            color: "#bbf6ef"
                        }

                        // Sample Name
                        Row {
                            spacing: 8
                            anchors.horizontalCenter: parent.horizontalCenter

                            Text {
                                width: 130
                                text: "Sample Name:"
                                font.pixelSize: 11
                                font.family: "Courier"
                                color: "#ffffff"
                                verticalAlignment: Text.AlignVCenter
                                height: 22
                            }

                            Rectangle {
                                width: 200
                                height: 22
                                color: "#000000"
                                border.width: 1

                                TextInput {
                                    id: sampleNameInput
                                    anchors.fill: parent
                                    anchors.margins: 2
                                    text: "sample"
                                    font.pixelSize: 12
                                    font.family: "Cascadia Mono"
                                    color: "#ff6d00"
                                    verticalAlignment: Text.AlignVCenter
                                    onEditingFinished: XWingScanBackend.setSampleName(text)
                                }
                            }
                        }

                        // Nx and Ny
                        Row {
                            spacing: 20
                            anchors.horizontalCenter: parent.horizontalCenter

                            Row {
                                spacing: 8

                                Text {
                                    width: 65
                                    text: "Nx (cols):"
                                    font.pixelSize: 11
                                    font.family: "Courier"
                                    color: "#ffffff"
                                    verticalAlignment: Text.AlignVCenter
                                    height: 22
                                }

                                Rectangle {
                                    width: 50
                                    height: 22
                                    color: "#000000"
                                    border.width: 1

                                    TextInput {
                                        id: nxInput
                                        anchors.fill: parent
                                        anchors.margins: 2
                                        text: "5"
                                        font.pixelSize: 12
                                        font.family: "Cascadia Mono"
                                        color: "#ff6d00"
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        onEditingFinished: XWingScanBackend.setNx(text)
                                    }
                                }
                            }

                            Row {
                                spacing: 8

                                Text {
                                    width: 65
                                    text: "Ny (rows):"
                                    font.pixelSize: 11
                                    font.family: "Courier"
                                    color: "#ffffff"
                                    verticalAlignment: Text.AlignVCenter
                                    height: 22
                                }

                                Rectangle {
                                    width: 50
                                    height: 22
                                    color: "#000000"
                                    border.width: 1

                                    TextInput {
                                        id: nyInput
                                        anchors.fill: parent
                                        anchors.margins: 2
                                        text: "5"
                                        font.pixelSize: 12
                                        font.family: "Cascadia Mono"
                                        color: "#ff6d00"
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        onEditingFinished: XWingScanBackend.setNy(text)
                                    }
                                }
                            }
                        }

                        // Integration time
                        Row {
                            spacing: 8
                            anchors.horizontalCenter: parent.horizontalCenter

                            Text {
                                width: 130
                                text: "Integration (µs):"
                                font.pixelSize: 11
                                font.family: "Courier"
                                color: "#ffffff"
                                verticalAlignment: Text.AlignVCenter
                                height: 22
                            }

                            Rectangle {
                                width: 100
                                height: 22
                                color: "#000000"
                                border.width: 1

                                TextInput {
                                    id: integrationInput
                                    anchors.fill: parent
                                    anchors.margins: 2
                                    text: "500000"
                                    font.pixelSize: 12
                                    font.family: "Cascadia Mono"
                                    color: "#ff6d00"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    onEditingFinished: XWingScanBackend.setIntegrationTime(text)
                                }
                            }
                        }
                    }
                }
            }

            // Panel C – Progress display
            Rectangle {
                width: 400
                height: 80
                color: "#313131"
                border.width: 3

                Rectangle {
                    x: 8
                    y: 8
                    width: 384
                    height: 64
                    color: "#4d4d4d"
                    radius: 5
                    border.width: 2

                    Column {
                        anchors.centerIn: parent
                        spacing: 6

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Progress"
                            font.pixelSize: 12
                            font.family: "Courier"
                            color: "#bbf6ef"
                        }

                        Text {
                            id: progressText
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "—"
                            font.pixelSize: 18
                            font.family: "Cascadia Mono"
                            color: "#ff6d00"
                        }
                    }
                }

                Connections {
                    target: XWingScanBackend
                    function onProgressChanged(msg) { progressText.text = msg }
                }
            }

            // Panel D – Status bar
            Rectangle {
                width: 400
                height: 60
                color: "#2d2d2d"
                border.width: 2

                Text {
                    id: statusText
                    anchors.centerIn: parent
                    text: "Ready"
                    font.pixelSize: 14
                    font.family: "Courier"
                    color: "#43ac33"
                }

                Connections {
                    target: XWingScanBackend
                    function onStatusChanged(msg) { statusText.text = msg }
                }
            }

            // Panel E – Start / Stop buttons
            Rectangle {
                width: 400
                height: 50
                color: "#313131"
                border.width: 3

                Row {
                    anchors.centerIn: parent
                    spacing: 10

                    Button {
                        width: 180
                        height: 30
                        text: "Start Scan"
                        onClicked: XWingScanBackend.threading()

                        background: Rectangle {
                            anchors.fill: parent
                            color: "#149700"
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

                    Button {
                        width: 90
                        height: 30
                        text: "Stop"
                        onClicked: XWingScanBackend.stopScan()

                        background: Rectangle {
                            anchors.fill: parent
                            color: "#d80000"
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

            // Filler
            Rectangle {
                width: 400
                height: 460
                color: "#6f6f6f"
            }
        }
    }
}
