import QtQuick
import QtQuick.Controls

Window {
    id: cameraViewPopup
    width: 760
    height: 640
    title: "TL Camera Live View"
    color: "#2d2d2d"

    onClosing: tlCameraCore.stopLiveView()

    Rectangle {
        id: background
        anchors.fill: parent
        color: "#313131"

        Text {
            id: titleLabel
            x: 15
            y: 10
            color: "#bbf6ef"
            text: "TL Camera Live View"
            font.pixelSize: 16
            font.styleName: "Bold"
            font.family: "Courier"
        }

        // Live frame display
        Rectangle {
            id: frameContainer
            x: 10
            y: 36
            width: 740
            height: 556
            color: "#000000"
            border.width: 2
            border.color: "#4d4d4d"

            Image {
                id: liveImage
                anchors.fill: parent
                source: tlCameraCore.liveFrame
                fillMode: Image.PreserveAspectFit
                cache: false
            }
        }

        // Status label
        Text {
            id: statusLabel
            x: 15
            y: 603
            color: "#ff6d00"
            text: tlCameraCore.status
            font.pixelSize: 12
            font.family: "Courier"
        }

        // Exposure label
        Text {
            x: 210
            y: 601
            color: "#b9f4ed"
            text: "Exp (ms):"
            font.pixelSize: 12
            font.family: "Courier"
        }

        // Exposure input
        Rectangle {
            id: exposureInputBg
            x: 290
            y: 598
            width: 72
            height: 22
            color: "#000000"
            border.width: 2

            TextInput {
                id: exposureInput
                anchors.fill: parent
                anchors.margins: 2
                color: "#ff6d00"
                text: tlCameraCore.exposure.toFixed(1)
                font.pixelSize: 12
                font.family: "OCR A"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                onEditingFinished: tlCameraCore.setExposure(text)
            }
        }

        // Set exposure button
        Rectangle {
            id: setExposureRect
            x: 368
            y: 598
            width: 40
            height: 22
            color: "#4d4d4d"
            border.width: 2
            radius: 3

            Button {
                anchors.fill: parent
                text: "Set"
                font.family: "Arial"
                font.pointSize: 8
                onClicked: tlCameraCore.setExposure(exposureInput.text)
                background: Rectangle { color: "transparent" }
                contentItem: Text {
                    text: parent.text
                    font: parent.font
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        // Start Live button
        Rectangle {
            id: startButtonRect
            x: 430
            y: 596
            width: 80
            height: 26
            color: "#149700"
            border.width: 2
            radius: 5

            Button {
                anchors.fill: parent
                text: "Start Live"
                font.family: "Arial"
                font.pointSize: 8
                onClicked: tlCameraCore.startLiveView()
                background: Rectangle { color: "transparent" }
                contentItem: Text {
                    text: parent.text
                    font: parent.font
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        // Stop Live button
        Rectangle {
            id: stopButtonRect
            x: 518
            y: 596
            width: 80
            height: 26
            color: "#d80000"
            border.width: 2
            radius: 5

            Button {
                anchors.fill: parent
                text: "Stop Live"
                font.family: "Arial"
                font.pointSize: 8
                onClicked: tlCameraCore.stopLiveView()
                background: Rectangle { color: "transparent" }
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
