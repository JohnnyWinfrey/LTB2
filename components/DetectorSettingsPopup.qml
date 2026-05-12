// DetectorSettingsPopup.qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Window {
    id: detectorSettingsPopup
    width: 300
    height: 260
    title: "Detector Settings"
    color: "#2d2d2d"

    property string detectorType: "pmt"

    // Map detectorType to stack index
    readonly property int _stackIndex: detectorType === "spectrometer" ? 1
                                     : detectorType === "camera"       ? 2
                                     : 0

    Rectangle {
        anchors.fill: parent
        color: "#313131"

        Text {
            id: titleLabel
            x: 15; y: 10
            color: "#bbf6ef"
            text: "Detector Settings"
            font.pixelSize: 16
            font.styleName: "Bold"
            font.family: "Courier"
        }

        // Divider
        Rectangle {
            x: 10; y: 34
            width: 280; height: 2
            color: "#4d4d4d"
        }

        StackLayout {
            x: 10; y: 44
            width: 280
            height: 170
            currentIndex: detectorSettingsPopup._stackIndex

            // ── Panel 0: PMT ───────────────────────────────────────────────
            Rectangle {
                color: "#3d3d3d"
                radius: 8

                Column {
                    anchors.centerIn: parent
                    spacing: 10

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "PMT Gain Shield"
                        font.pixelSize: 13
                        font.family: "Courier"
                        color: "#bbf6ef"
                    }

                    // Current gain display
                    Rectangle {
                        width: 220; height: 52
                        color: "#4d4d4d"
                        radius: 5
                        border.width: 2
                        border.color: "#000000"

                        Text {
                            x: 10; y: 5
                            color: "#b9f4ed"
                            text: "Current Gain"
                            font.pixelSize: 11
                            font.family: "Courier"
                        }
                        Rectangle {
                            x: 10; y: 24
                            width: 200; height: 22
                            color: "#000000"
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                color: "#ff6d00"
                                text: PMTGainShieldBackend.gain.toFixed(3)
                                font.pixelSize: 16
                                font.family: "OCR A"
                            }
                        }
                    }

                    // Set gain row
                    Row {
                        spacing: 6
                        Text {
                            width: 60
                            text: "Set Gain:"
                            font.pixelSize: 11
                            font.family: "Courier"
                            color: "#b9f4ed"
                            verticalAlignment: Text.AlignVCenter
                            height: 26
                        }
                        Rectangle {
                            width: 110; height: 26
                            color: "#000000"
                            border.width: 2
                            TextInput {
                                id: pmtGainInput
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
                            width: 44; height: 26
                            color: "#149700"
                            border.width: 2
                            radius: 5
                            Button {
                                anchors.fill: parent
                                text: "Set"
                                font.family: "Arial"
                                font.pointSize: 8
                                onClicked: PMTGainShieldBackend.changeGain(pmtGainInput.text)
                                background: Rectangle { color: "transparent" }
                                contentItem: Text {
                                    text: parent.text; font: parent.font
                                    color: "#ffffff"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }
                    }
                }
            }

            // ── Panel 1: Spectrometer ─────────────────────────────────────
            Rectangle {
                color: "#3d3d3d"
                radius: 8

                Column {
                    anchors.centerIn: parent
                    spacing: 10

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Spectrometer"
                        font.pixelSize: 13
                        font.family: "Courier"
                        color: "#bbf6ef"
                    }

                    // Status + connect row
                    Row {
                        spacing: 8
                        Text {
                            id: spectroStatusText
                            text: XWingScanBackend.spectroStatus
                            font.pixelSize: 10
                            font.family: "Courier"
                            color: XWingScanBackend.spectroStatus === "Connected" ? "#00e676" : "#ff6d00"
                            verticalAlignment: Text.AlignVCenter
                            height: 26
                            width: 150
                        }
                        Rectangle {
                            width: 80; height: 26
                            color: "#00579e"
                            border.width: 2
                            radius: 5
                            Button {
                                anchors.fill: parent
                                text: "Connect"
                                font.family: "Arial"
                                font.pointSize: 8
                                onClicked: XWingScanBackend.connectSpectrometer()
                                background: Rectangle { color: "transparent" }
                                contentItem: Text {
                                    text: parent.text; font: parent.font
                                    color: "#ffffff"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }
                    }

                    // Integration time
                    Row {
                        spacing: 6
                        enabled: XWingScanBackend.spectroStatus === "Connected"
                        opacity: enabled ? 1.0 : 0.4
                        Text {
                            width: 80; text: "Int (μs):"
                            font.pixelSize: 11; font.family: "Courier"
                            color: "#b9f4ed"; verticalAlignment: Text.AlignVCenter; height: 24
                        }
                        Rectangle {
                            width: 120; height: 24
                            color: "#000000"; border.width: 2
                            TextInput {
                                id: spectroIntInput
                                anchors.fill: parent; anchors.margins: 2
                                color: "#ff6d00"; text: "500000"
                                font.pixelSize: 12; font.family: "Courier"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                onEditingFinished: XWingScanBackend.setSpectroIntegration(text)
                            }
                        }
                    }

                    // Scans to average
                    Row {
                        spacing: 6
                        enabled: XWingScanBackend.spectroStatus === "Connected"
                        opacity: enabled ? 1.0 : 0.4
                        Text {
                            width: 80; text: "Scans Avg:"
                            font.pixelSize: 11; font.family: "Courier"
                            color: "#b9f4ed"; verticalAlignment: Text.AlignVCenter; height: 24
                        }
                        Rectangle {
                            width: 120; height: 24
                            color: "#000000"; border.width: 2
                            TextInput {
                                id: spectroAvgInput
                                anchors.fill: parent; anchors.margins: 2
                                color: "#ff6d00"; text: "1"
                                font.pixelSize: 12; font.family: "Courier"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                onEditingFinished: XWingScanBackend.setSpectroScansAvg(text)
                            }
                        }
                    }
                }
            }

            // ── Panel 2: Camera ───────────────────────────────────────────
            Rectangle {
                color: "#3d3d3d"
                radius: 8

                Column {
                    anchors.centerIn: parent
                    spacing: 10

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "TL Camera"
                        font.pixelSize: 13
                        font.family: "Courier"
                        color: "#bbf6ef"
                    }

                    // Status display
                    Rectangle {
                        width: 220; height: 28
                        color: "#4d4d4d"
                        radius: 4
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: tlCameraCore.status
                            font.pixelSize: 12
                            font.family: "Courier"
                            color: tlCameraCore.status === "Connected" || tlCameraCore.status === "Live"
                                   ? "#00e676" : "#ff6d00"
                        }
                    }

                    // Exposure row
                    Row {
                        spacing: 6
                        Text {
                            width: 80; text: "Exp (ms):"
                            font.pixelSize: 11; font.family: "Courier"
                            color: "#b9f4ed"; verticalAlignment: Text.AlignVCenter; height: 26
                        }
                        Rectangle {
                            width: 90; height: 26
                            color: "#000000"; border.width: 2
                            TextInput {
                                id: cameraExpInput
                                anchors.fill: parent; anchors.margins: 2
                                color: "#ff6d00"
                                text: tlCameraCore.exposure.toFixed(1)
                                font.pixelSize: 13; font.family: "OCR A"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                onEditingFinished: tlCameraCore.setExposure(text)
                            }
                        }
                        Rectangle {
                            width: 44; height: 26
                            color: "#149700"; border.width: 2; radius: 5
                            Button {
                                anchors.fill: parent
                                text: "Set"
                                font.family: "Arial"; font.pointSize: 8
                                onClicked: tlCameraCore.setExposure(cameraExpInput.text)
                                background: Rectangle { color: "transparent" }
                                contentItem: Text {
                                    text: parent.text; font: parent.font
                                    color: "#ffffff"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }
                    }
                }
            }
        }

        // Close button
        Rectangle {
            x: 110; y: 222
            width: 80; height: 28
            color: "#676767"; border.width: 2; radius: 5

            Button {
                anchors.fill: parent
                text: "Close"
                font.family: "Courier"; font.pointSize: 9
                onClicked: detectorSettingsPopup.visible = false
                background: Rectangle { color: "transparent" }
                contentItem: Text {
                    text: parent.text; font: parent.font
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
}
