// XWingSimpleController.qml
// Same as XWingController but without position memory, radio buttons, Store/Recall.
import QtQuick
import QtQuick.Controls

Rectangle {
    id: xwingSimpleController
    width: 200
    height: 240
    color: "#6f6f6f"
    radius: 5
    border.width: 2

    // X position display
    Rectangle {
        x: 0; y: 0
        width: 100; height: 80
        color: "#4d4d4d"
        border.color: "#000000"
        bottomLeftRadius: 10; topLeftRadius: 10
        scale: 0.9

        Rectangle {
            x: 8; y: 5; width: 84; height: 37
            color: "#000000"
        }

        Label {
            x: 23; y: 4; width: 55; height: 40
            color: "#ff6d00"
            text: XWingBackend.xPosString
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.pointSize: 20
            font.family: "Cascadia Mono"
            scale: 0.9
        }

        Label {
            x: 8; y: 48
            text: "X (mm)"
            font.wordSpacing: -0.5
            font.family: "Cascadia Mono"
            font.pointSize: 17
        }
    }

    // Y position display
    Rectangle {
        x: 100; y: 0
        width: 100; height: 80
        color: "#4d4d4d"
        border.width: 1
        bottomRightRadius: 10; topRightRadius: 10
        scale: 0.9

        Rectangle {
            x: 8; y: 5; width: 84; height: 37
            color: "#000000"
        }

        Label {
            x: 22; y: 4; width: 55; height: 40
            color: "#ff6d00"
            text: XWingBackend.yPosString
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.family: "Cascadia Mono"
            font.pointSize: 21
            scale: 0.9
        }

        Label {
            x: 8; y: 48
            text: "Y (mm)"
            font.wordSpacing: -0.5
            font.pointSize: 17
            font.family: "Cascadia Mono"
        }
    }

    // Home button
    Rectangle {
        x: 8; y: 82; width: 43; height: 18
        color: "#d600cd"
        radius: 10
    }

    Button {
        x: 8; y: 82; width: 43; height: 18
        text: "Home"
        font.family: "Consolas"
        font.pointSize: 7
        onClicked: XWingBackend.home()
    }

    // Up
    Button {
        x: 73; y: 86; width: 55; height: 40
        text: "Up"
        font.family: "Consolas"
        onClicked: XWingBackend.moveUp()
        background: Rectangle {
            color: "#00ffdf"; border.width: 2
            topRightRadius: 10; topLeftRadius: 10
        }
    }

    // Down
    Button {
        x: 73; y: 132; width: 55; height: 40
        text: "Down"
        font.family: "Consolas"
        onClicked: XWingBackend.moveDown()
        background: Rectangle { color: "#00ffdf"; border.width: 2 }
    }

    // Left
    Button {
        x: 12; y: 132; width: 55; height: 40
        text: "Left"
        font.family: "Consolas"
        onClicked: XWingBackend.moveLeft()
        background: Rectangle {
            color: "#ff563e"; border.width: 2
            topLeftRadius: 10; bottomLeftRadius: 10
        }
    }

    // Right
    Button {
        x: 135; y: 132; width: 55; height: 40
        text: "Right"
        font.family: "Consolas"
        onClicked: XWingBackend.moveRight()
        background: Rectangle {
            color: "#ff563e"; border.width: 2
            topRightRadius: 10; bottomRightRadius: 10
        }
    }

    // Go To: X input, Y input, Go! button
    Rectangle {
        x: 10; y: 182
        width: 180; height: 48
        color: "#4d4d4d"
        border.width: 1
        radius: 8

        Row {
            anchors.centerIn: parent
            spacing: 5

            Rectangle {
                width: 58; height: 26; color: "#000000"; border.width: 1

                TextInput {
                    id: xGoTo
                    anchors.fill: parent; anchors.margins: 2
                    text: "0.000"
                    color: "#ff6d00"
                    font.pixelSize: 13; font.family: "Cascadia Mono"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Rectangle {
                width: 58; height: 26; color: "#000000"; border.width: 1

                TextInput {
                    id: yGoTo
                    anchors.fill: parent; anchors.margins: 2
                    text: "0.000"
                    color: "#ff6d00"
                    font.pixelSize: 13; font.family: "Cascadia Mono"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Rectangle {
                width: 42; height: 26; color: "#017a03"; border.width: 2; radius: 5

                Button {
                    anchors.fill: parent
                    text: "Go!"
                    font.family: "Consolas"; font.pointSize: 8
                    onClicked: XWingBackend.setPosition(xGoTo.text, yGoTo.text)
                    background: Rectangle { color: "transparent" }
                    contentItem: Text {
                        text: parent.text; font: parent.font; color: "#ffffff"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }
}
