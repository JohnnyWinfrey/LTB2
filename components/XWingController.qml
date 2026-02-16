import QtQuick
import QtQuick.Controls

Rectangle {
    id: xwingController
    width: 200
    height: 351
    color: "#6f6f6f"
    radius: 5
    border.width: 2
    
    

    Button {
        id: moveUp
        x: 73
        y: 86
        width: 55
        height: 40
        text: qsTr("Up")
        font.family: "Consolas"
        icon.color: "#b23a3a"
        onClicked: XWingBackend.moveUp()
        background: Rectangle {
            id: rectangle10
            x: 0
            y: 0
            width: 56
            height: 40
            color: "#00ffdf"
            border.width: 2
            topRightRadius: 10
            topLeftRadius: 10
        }
    }
    

    

    Button {
        id: moveDown
        x: 73
        y: 132
        width: 55
        height: 40
        text: qsTr("Down")
        font.family: "Consolas"
        onClicked: XWingBackend.moveDown()
        background: Rectangle {
            id: rectangle11
            x: 0
            y: 0
            width: 56
            height: 40
            color: "#00ffdf"
            border.width: 2
        }
    }
    

    

    Button {
        id: moveRight
        x: 135
        y: 132
        width: 55
        height: 40
        text: qsTr("Right")
        font.family: "Consolas"
        onClicked: XWingBackend.moveRight()
        background: Rectangle {
            id: rectangle12
            x: 0
            y: 0
            width: 56
            height: 40
            color: "#ff563e"
            border.width: 2
            topRightRadius: 10
            bottomRightRadius: 10
        }
    }
    

    

    Button {
        id: moveLeft
        x: 12
        y: 132
        width: 55
        height: 40
        text: qsTr("Left")
        font.family: "Consolas"
        onClicked: XWingBackend.moveLeft()
        background: Rectangle {
            id: rectangle13
            x: 0
            y: 0
            width: 56
            height: 40
            color: "#ff563e"
            border.width: 2
            topLeftRadius: 10
            bottomLeftRadius: 10
        }

    }
    

    Rectangle {
        id: rectangle1
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
            id: rectangle
            x: 8
            y: 5
            width: 84
            height: 37
            color: "#000000"
        }

        Label {
            id: xPosition
            x: 23
            y: 4
            width: 55
            height: 40
            color: "#ff6d00"
            text: XWingBackend.xPosString
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.pointSize: 20
            font.family: "Cascadia Mono"
            scale: 0.9
        }


        Label {
            id: label
            x: 8
            y: 48
            text: qsTr("X (mm)")
            font.wordSpacing: -0.5
            font.family: "Cascadia Mono"
            font.pointSize: 17
        }

    }
    

    Rectangle {
        id: rectangle2
        x: 100
        y: 0
        width: 100
        height: 80
        color: "#4d4d4d"
        border.width: 1
        bottomRightRadius: 10
        topRightRadius: 10
        topLeftRadius: 0
        scale: 0.9
        
        Rectangle {
            id: rectangle3
            x: 8
            y: 5
            width: 84
            height: 37
            color: "#000000"
        }

        Label {
            id: yPosition
            x: 22
            y: 4
            width: 55
            height: 40
            color: "#ff6d00"
            text: XWingBackend.yPosString
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.family: "Cascadia Mono"
            font.pointSize: 21
            scale: 0.9
        }


        Label {
            id: label1
            x: 8
            y: 48
            text: qsTr("Y (mm)")
            font.wordSpacing: -0.5
            font.pointSize: 17
            font.family: "Cascadia Mono"
        }

    }
    

    Rectangle {
        id: rectangle14
        x: 8
        y: 82
        width: 43
        height: 18
        color: "#d600cd"
        radius: 10
    }

    Button {
        id: home
        x: 8
        y: 82
        width: 43
        height: 18
        text: qsTr("Home")
        icon.color: "#00000000"
        font.family: "Consolas"
        font.pointSize: 7
        onClicked: XWingBackend.home()
    }
    

    Rectangle {
        id: cordinates
        x: 10
        y: 178
        width: 180
        height: 165
        color: "#4d4d4d"
        border.width: 1
        topLeftRadius: 20
        


        Rectangle {
            id: rectangle4
            x: 0
            y: 0
            width: 180
            height: 77
            color: "#000000"
            bottomRightRadius: 20
            topLeftRadius: 20
        }


        Label {
            id: yGoTo
            x: 122
            y: 115
            width: 55
            height: 16
            text: qsTr("Y (mm)")
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.wordSpacing: -0.7
            font.family: "Cascadia Mono"
        }
        





        Label {
            id: xGoTo
            x: 65
            y: 115
            width: 55
            height: 16
            text: qsTr("X (mm)")
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.wordSpacing: -0.8
            font.family: "Cascadia Mono"
        }
        




        Rectangle {
            id: rectangle5
            x: 65
            y: 89
            width: 112
            height: 20
            color: "#000000"
        }



        TextInput {
            id: xSetPosition
            x: 65
            y: 89
            width: 55
            height: 20
            color: "#ff6d00"
            text: qsTr("0.000")
            font.pixelSize: 17
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.family: "Cascadia Mono"
        }
        




        TextInput {
            id: ySetPosition
            x: 122
            y: 89
            width: 54
            height: 20
            color: "#ff6d00"
            text: qsTr("0.000")
            font.pixelSize: 17
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.family: "Cascadia Mono"
        }
        



        Rectangle {
            id: rectangle9
            x: 83
            y: 137
            width: 76
            height: 20
            color: "#017a03"
            radius: 0
            border.width: 2
            bottomRightRadius: 0
            topRightRadius: 27
            bottomLeftRadius: 7
            topLeftRadius: 0
        }

        Button {
            id: setPosition
            x: 83
            y: 137
            width: 76
            height: 20
            text: qsTr("Go!")
            font.family: "Consolas"
            onClicked: XWingBackend.setPosition(xSetPosition.text, ySetPosition.text)
        }
        


        Text {
            id: text1
            x: 8
            y: 52
            color: "#ff6d00"
            text: qsTr("Position Memory")
            font.pixelSize: 18
            font.family: "Cascadia Mono"
        }

        Rectangle {
            id: rectangle6
            x: 4
            y: 89
            width: 57
            height: 18
            color: "#017a03"
            border.width: 2
        }

        Button {
            id: setHome
            x: 4
            y: 89
            width: 57
            height: 18
            text: qsTr("Set Home")
            font.family: "Consolas"
            font.pointSize: 7
            onClicked: XWingBackend.setHome()
        }



        Image {
            id: image
            x: 124
            y: -97
            width: 54
            height: 46
            source: "x-wing.png"
            rotation: 20.014
            fillMode: Image.PreserveAspectFit
        }



        Text {
            id: text2
            x: 13
            y: 29
            color: "#ffffff"
            text: qsTr("1")
            font.pixelSize: 17
            font.family: "Cascadia Mono"
        }

        RadioButton {
            id: radioButton
            x: 0
            y: 2
            width: 35
            height: 32
            text: qsTr("")
            display: AbstractButton.IconOnly
            onClicked: XWingBackend.memSelected(1)
        }



        RadioButton {
            id: radioButton1
            x: 41
            y: 2
            width: 35
            height: 32
            text: qsTr("")
            display: AbstractButton.IconOnly
            onClicked: XWingBackend.memSelected(3)
        }



        RadioButton {
            id: radioButton2
            x: 82
            y: 2
            width: 35
            height: 32
            text: qsTr("")
            display: AbstractButton.IconOnly
            onClicked: XWingBackend.memSelected(5)
        }



        RadioButton {
            id: radioButton3
            x: 123
            y: 2
            width: 35
            height: 32
            text: qsTr("")
            display: AbstractButton.IconOnly
            onClicked: XWingBackend.memSelected(7)
        }



        RadioButton {
            id: radioButton4
            x: 22
            y: 22
            width: 35
            height: 32
            text: qsTr("")
            display: AbstractButton.IconOnly
            onClicked: XWingBackend.memSelected(2)
        }



        RadioButton {
            id: radioButton5
            x: 63
            y: 22
            width: 35
            height: 32
            text: qsTr("")
            display: AbstractButton.IconOnly
            onClicked: XWingBackend.memSelected(4)
        }



        RadioButton {
            id: radioButton6
            x: 104
            y: 22
            width: 35
            height: 32
            text: qsTr("")
            display: AbstractButton.IconOnly
            onClicked: XWingBackend.memSelected(6)
        }



        RadioButton {
            id: radioButton7
            x: 145
            y: 22
            width: 35
            height: 32
            text: qsTr("")
            display: AbstractButton.IconOnly
            onClicked: XWingBackend.memSelected(8)
        }



        Rectangle {
            id: rectangle7
            x: 12
            y: 113
            width: 41
            height: 18
            color: "#ff6d00"
            border.width: 2
        }

        Button {
            id: setHome1
            x: 12
            y: 113
            width: 41
            height: 18
            text: qsTr("Store")
            font.family: "Consolas"
            font.pointSize: 7
            onClicked: XWingBackend.storeCoordinates(x, y)

        }

        Rectangle {
            id: rectangle8
            x: 4
            y: 137
            width: 57
            height: 18
            color: "#0900ff"
            border.width: 2
        }

        Button {
            id: setHome2
            x: 4
            y: 137
            width: 57
            height: 18
            text: qsTr("Recall")
            font.family: "Consolas"
            font.pointSize: 7
            onClicked: XWingBackend.recall()
        }

        Text {
            id: text3
            x: 35
            y: 7
            color: "#ffffff"
            text: qsTr("2")
            font.pixelSize: 17
            font.family: "Cascadia Mono"
        }

        Text {
            id: text5
            x: 54
            y: 29
            width: 9
            height: 22
            color: "#ffffff"
            text: qsTr("3")
            font.pixelSize: 17
            font.family: "Cascadia Mono"
        }

        Text {
            id: text6
            x: 75
            y: 8
            width: 9
            height: 22
            color: "#ffffff"
            text: qsTr("4")
            font.pixelSize: 17
            font.family: "Cascadia Mono"
        }

        Text {
            id: text7
            x: 95
            y: 29
            width: 9
            height: 22
            color: "#ffffff"
            text: qsTr("5")
            font.pixelSize: 17
            font.family: "Cascadia Mono"
        }

        Text {
            id: text8
            x: 116
            y: 7
            width: 9
            height: 22
            color: "#ffffff"
            text: qsTr("6")
            font.pixelSize: 17
            font.family: "Cascadia Mono"
        }

        Text {
            id: text9
            x: 136
            y: 29
            width: 9
            height: 22
            color: "#ffffff"
            text: qsTr("7")
            font.pixelSize: 17
            font.family: "Cascadia Mono"
        }

        Text {
            id: text10
            x: 158
            y: 7
            width: 9
            height: 22
            color: "#ffffff"
            text: qsTr("8")
            font.pixelSize: 17
            font.family: "Cascadia Mono"
        }


    }

}
