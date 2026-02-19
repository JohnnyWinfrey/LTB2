// PositionManager.qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: positionManager
    width: 400
    height: 350  // Increased from 250
    color: "#313131"
    border.width: 3

    Rectangle {
        id: background
        x: 8
        y: 8
        width: 384
        height: 334  // Increased from 234
        color: "#676767"
        radius: 5
        border.width: 2

        Text {
            id: title
            x: 10
            y: 5
            color: "#bbf6ef"
            text: "Position Manager"
            font.pixelSize: 14
            font.styleName: "Bold"
            font.family: "Courier"
        }

        // Reference section
        Rectangle {
            x: 10
            y: 30
            width: 364
            height: 50
            color: "#4d4d4d"
            radius: 5
            border.width: 2

            Text {
                x: 10
                y: 5
                color: "#43ac33"
                text: "Reference Position"
                font.pixelSize: 12
                font.styleName: "Bold"
                font.family: "Courier"
            }

            Text {
                id: refDisplay
                x: 10
                y: 25
                color: "#ffffff"
                text: XWingBackend.referencePosition.x !== undefined ? 
                      "X: " + XWingBackend.referencePosition.x.toFixed(2) + 
                      " Y: " + XWingBackend.referencePosition.y.toFixed(2) : 
                      "No reference set"
                font.pixelSize: 10
                font.family: "Courier"
            }

            Button {
                x: 240
                y: 20
                width: 50
                height: 25
                text: "Store"
                font.pixelSize: 8
                onClicked: XWingBackend.storeReference()
                
                background: Rectangle {
                    anchors.fill: parent
                    color: "#149700"
                    border.width: 2
                }
            }

            Button {
                x: 295
                y: 20
                width: 50
                height: 25
                text: "Clear"
                font.pixelSize: 8
                onClicked: XWingBackend.clearReference()
                
                background: Rectangle {
                    anchors.fill: parent
                    color: "#d80000"
                    border.width: 2
                }
            }
        }

        // Sample section
        Text {
            x: 10
            y: 90
            color: "#2196F3"
            text: "Sample Positions"
            font.pixelSize: 12
            font.styleName: "Bold"
            font.family: "Courier"
        }

        RowLayout {
            x: 10
            y: 110
            width: 364
            spacing: 5

            ComboBox {
                id: regionCombo
                Layout.preferredWidth: 100
                model: ["A", "B", "C", "D", "Other"]
                currentIndex: 0
            }

            Button {
                id: storeButton
                Layout.preferredWidth: 100
                text: "Store Sample"
                onClicked: {
                    XWingBackend.storeSample(regionCombo.currentText)
                }
                
                background: Rectangle {
                    anchors.fill: parent
                    color: "#149700"
                    border.width: 2
                }
            }

            Button {
                id: clearButton
                Layout.preferredWidth: 100
                text: "Clear All"
                onClicked: XWingBackend.clearSamples()
                
                background: Rectangle {
                    anchors.fill: parent
                    color: "#d80000"
                    border.width: 2
                }
            }
        }

        ListView {
            id: sampleList
            x: 10
            y: 145
            width: 364
            height: 180  // Increased from 80
            clip: true

            model: ListModel {
                id: sampleModel
            }

            delegate: Rectangle {
                width: sampleList.width
                height: 25
                color: index % 2 === 0 ? "#4d4d4d" : "#3d3d3d"
                border.width: 1
                border.color: "#000000"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 5
                    spacing: 10

                    Text {
                        Layout.preferredWidth: 70
                        color: "#2196F3"
                        text: "Region " + model.region
                        font.pixelSize: 10
                        font.family: "Courier"
                    }

                    Text {
                        Layout.fillWidth: true
                        color: "#ffffff"
                        text: "X: " + model.x.toFixed(2) + " Y: " + model.y.toFixed(2)
                        font.pixelSize: 10
                        font.family: "Courier"
                    }

                    Button {
                        Layout.preferredWidth: 45
                        Layout.preferredHeight: 20
                        text: "Go To"
                        font.pixelSize: 7
                        onClicked: {
                            XWingBackend.setPosition(
                                model.x.toString(),
                                model.y.toString()
                            )
                        }
                        
                        background: Rectangle {
                            anchors.fill: parent
                            color: "#2196F3"
                            border.width: 1
                        }
                    }

                    Button {
                        Layout.preferredWidth: 45
                        Layout.preferredHeight: 20
                        text: "Remove"
                        font.pixelSize: 7
                        onClicked: XWingBackend.removeSample(index)
                        
                        background: Rectangle {
                            anchors.fill: parent
                            color: "#d80000"
                            border.width: 1
                        }
                    }
                }
            }

            ScrollBar.vertical: ScrollBar {}
        }
    }

    // Connection to update lists when coordinates change
    Connections {
        target: XWingBackend
        function onCoordinatesChanged() {
            updateSampleList()
        }
    }

    Component.onCompleted: {
        updateSampleList()
    }

    function updateSampleList() {
        sampleModel.clear()
        
        // Read samples from Python backend
        var samples = XWingBackend.samplesList
        
        // Populate the ListView model
        for (var i = 0; i < samples.length; i++) {
            sampleModel.append({
                region: samples[i].region,
                x: samples[i].x,
                y: samples[i].y
            })
        }
    }
}