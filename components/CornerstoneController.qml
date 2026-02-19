import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.VirtualKeyboard.Styles

Row {
    id: cornerstoneController
    width: 400
    height: 300

    Rectangle {
        id: cornerstoneControllerPrimary
        width: 200
        height: 300
        color: "#313131"
        border.width: 3

        Rectangle {
            id: rectangle
            x: 8
            y: 40
            width: 184
            height: 163
            color: "#676767"
            border.width: 2
            topRightRadius: 10
            topLeftRadius: 10
        }

        Rectangle {
            id: rectangle4
            x: 8
            y: 207
            width: 184
            height: 85
            color: "#676767"
            border.width: 2
            bottomRightRadius: 10
            bottomLeftRadius: 10
        }

        Rectangle {
            id: rectangle5
            x: 32
            y: 245
            width: 60
            height: 35
            color: "#43ac33"
            border.width: 2

            Button {
                id: openShutter
                x: 0
                y: 0
                width: 60
                height: 35
                text: qsTr("Open")
                checkable: false
                flat: false
                highlighted: false
                onClicked: CornerstoneBackend.openShutter()

                Connections {
                    target: openShutter
                    function onClicked() {
                        closeShutter.highlighted = false
                    }
                }

                Connections {
                    target: openShutter
                    function onClicked() {
                        openShutter.highlighted = true
                    }
                }

                Connections {
                    target: openShutter
                    function onClicked() {
                        rectangle5.visible = true
                    }
                }
            }
        }

        Rectangle {
            id: rectangle6
            x: 98
            y: 245
            width: 60
            height: 35
            color: "#d80000"
            border.width: 2

            Button {
                id: closeShutter
                x: 0
                y: 0
                width: 60
                height: 35
                text: qsTr("Close")
                flat: false
                highlighted: false
                onClicked: CornerstoneBackend.closeShutter()

                Connections {
                    target: closeShutter
                    function onClicked() {
                        openShutter.highlighted = false
                    }
                }

                Connections {
                    target: closeShutter
                    function onClicked() {
                        closeShutter.highlighted = true
                    }
                }

                Connections {
                    target: closeShutter
                    function onClicked() {
                        cornerstoneController.state = ""
                    }
                }
            }
        }

        Rectangle {
            id: rectangle2
            x: 33
            y: 114
            width: 125
            height: 26
            color: "#ffffff"
            border.width: 2

            TextInput {
                id: setWavelength
                x: 28
                y: 3
                width: 80
                height: 20
                text: "630"
                font.pixelSize: 12
                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
                font.underline: false
            }
        }

        Rectangle {
            id: rectangle1
            x: 33
            y: 68
            width: 125
            height: 26
            color: "#ffffff"
            border.width: 2

            Text {
                id: currentWavelength
                x: 15
                y: 5
                text: CornerstoneBackend.wavePos
                font.pixelSize: 12
            }
        }

        Rectangle {
            id: rectangle3
            x: 38
            y: 143
            width: 114
            height: 44
            color: "#149700"
            border.width: 3

            Button {
                id: goToWavelength
                x: 0
                y: 0
                width: 114
                height: 44
                opacity: 1
                text: qsTr("Go")
                highlighted: false
                clip: true
                display: AbstractButton.TextOnly
                icon.width: 44
                icon.height: 59
                icon.source: "button1.png"
                icon.cache: true
                icon.color: "#00ffffff"
                onClicked: CornerstoneBackend.setWavelength(setWavelength.text)
            }
        }

        Text {
            id: conerstoneControllerTitle
            x: 8
            y: 8
            width: 181
            height: 26
            color: "#bbf6ef"
            text: qsTr("Spectrograph Controller")
            font.pixelSize: 15
            horizontalAlignment: Text.AlignHCenter
            lineHeight: 1
            minimumPixelSize: 15
            fontSizeMode: Text.FixedSize
            font.underline: true
            font.bold: false
            font.weight: Font.Black
        }

        Button {
            id: button
            x: 8
            y: 8
            width: 184
            height: 26
            text: qsTr("Button")
            display: AbstractButton.IconOnly
        }

        Text {
            id: shutterControlLabel
            x: 19
            y: 219
            color: "#bbf6ef"
            text: qsTr("Shutter Controls")
            font.pixelSize: 17
            font.styleName: "Bold"
            font.family: "Courier"
        }

        Label {
            id: label
            x: 19
            y: 47
            color: "#b9f4ed"
            text: qsTr("Current Wavelength")
            font.styleName: "Bold"
            font.family: "Courier"
        }

        Label {
            id: label1
            x: 33
            y: 95
            color: "#b9f4ed"
            text: qsTr("Set Wavelength")
            font.styleName: "Bold"
            font.family: "Courier"
        }

        Text {
            id: currentWavelength1
            x: 164
            y: 119
            text: qsTr("nm")
            font.pixelSize: 12
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        Text {
            id: currentWavelength2
            x: 164
            y: 73
            text: qsTr("nm")
            font.pixelSize: 12
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    Rectangle {
        id: cornerstoneControllerAlt
        width: 200
        height: 300
        color: "#6f6f6f"
        border.width: 2

        ColumnLayout {
            id: columnLayout
            x: 0
            y: 0
            width: 200
            height: 150
            uniformCellSizes: false
            spacing: 0

            Rectangle {
                id: scanController
                width: 200
                height: columnLayout.height
                color: "#313131"
                border.width: 3

                Rectangle {
                    id: rectangle11
                    x: 8
                    y: 8
                    width: 184
                    height: 134
                    color: "#676767"
                    radius: 10
                    border.width: 3
                }

                Rectangle {
                    id: rectangle7
                    x: 83
                    y: 14
                    width: 81
                    height: 26
                    color: "#ffffff"
                    border.width: 2
                }

                TextInput {
                    id: startWavelength
                    x: 89
                    y: 17
                    width: 64
                    height: 20
                    text: "600"
                    font.pixelSize: 12
                    onEditingFinished: CornerstoneBackend.setStartWavelength(text)

                    Rectangle {
                        id: rectangle8
                        x: -6
                        y: 29
                        width: 81
                        height: 26
                        color: "#ffffff"
                        border.width: 2
                    }
                }

                TextInput {
                    id: endWavelength
                    x: 89
                    y: 49
                    width: 64
                    height: 20
                    text: "800"
                    font.pixelSize: 12
                    onEditingFinished: CornerstoneBackend.setEndWavelength(text)

                    Rectangle {
                        id: rectangle9
                        x: -6
                        y: 29
                        width: 101
                        height: 26
                        color: "#ffffff"
                        border.width: 2
                    }
                }

                TextInput {
                    id: numSteps
                    x: 94
                    y: 81
                    width: 80
                    height: 20
                    text: "50"
                    font.pixelSize: 12
                    onEditingFinished: CornerstoneBackend.setNumSteps(text)

                    Rectangle {
                        id: rectangle10
                        x: -73
                        y: 21
                        width: 50
                        height: 35
                        color: "#149700"
                        border.width: 3

                        Button {
                            id: startScan
                            x: 0
                            y: 0
                            width: 50
                            height: 35
                            text: qsTr("Scan")
                        }
                    }
                }

                Label {
                    id: label2
                    x: 14
                    y: 84
                    color: "#b9f4ed"
                    text: qsTr("# Steps")
                    font.styleName: "Bold"
                    font.family: "Courier"
                }

                Label {
                    id: label3
                    x: 23
                    y: 51
                    color: "#b9f4ed"
                    text: qsTr("End λ")
                    font.styleName: "Bold"
                    font.family: "Courier"
                }

                Label {
                    id: label4
                    x: 14
                    y: 19
                    color: "#b9f4ed"
                    text: qsTr("Start λ")
                    font.styleName: "Bold"
                    font.family: "Courier"
                }

                ProgressBar {
                    id: progressBar
                    x: 84
                    y: 115
                    value: 30
                    to: 100
                }

                Text {
                    id: currentWavelength3
                    x: 167
                    y: 19
                    text: qsTr("nm")
                    font.pixelSize: 12
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                Text {
                    id: currentWavelength4
                    x: 167
                    y: 51
                    text: qsTr("nm")
                    font.pixelSize: 12
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Rectangle {
                id: gratingController
                width: 200
                height: columnLayout.height
                color: "#313131"
                border.width: 3

                Rectangle {
                    id: rectangle12
                    x: 10
                    y: 8
                    width: 184
                    height: 134
                    color: "#676767"
                    radius: 9
                    border.width: 3
                }

                ComboBox {
                    id: gratings
                    x: 22
                    y: 59
                    width: 157
                    height: 32
                    displayText: "1"
                    editable: false
                    model: ["1", "2", "3"]
                    // displayText will automatically be the currently selected item
                    // so you usually don't need to set displayText manually
                }

                Rectangle {
                    id: rectangle13
                    x: 30
                    y: 97
                    width: 70
                    height: 35
                    color: "#149700"
                    border.width: 3

                    Button {
                        id: changeGrating
                        x: 0
                        y: 0
                        width: 70
                        height: 35
                        text: qsTr("Change")

                        Connections {
                            target: changeGrating
                            function onClicked() {
                                cornerstoneController.visible = cornerstoneController.visible
                            }
                        }
                    }
                }

                Text {
                    id: gratingLabel
                    x: 30
                    y: 27
                    color: "#bbf6ef"
                    text: qsTr("Select Grating")
                    font.pixelSize: 16
                    font.styleName: "Bold"
                    font.family: "Courier"
                }

                Image {
                    id: image
                    x: 114
                    y: 97
                    width: 56
                    height: 35
                    source: "Spectrograph Symbol.png"
                    fillMode: Image.PreserveAspectCrop
                }
            }
        }
    }
}