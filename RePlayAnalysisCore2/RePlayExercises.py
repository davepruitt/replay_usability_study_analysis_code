from enum import Enum
from py_linq import Enumerable

class RePlayDevice(Enum):
    ReCheck = 0
    FitMi = 1
    Touchscreen = 2
    Keyboard = 3
    ReTrieve = 4
    Unknown = 5

class RePlayExercises:

        #Tuple indices:
        #   0. Exercise name
        #   1. Exercise device
        #   2. Is a force-based exercise?
        #   3. Standard unit of measurement for this exercise

        exercises = [

            #ReCheck exercises
            ("Range of Motion Handle", RePlayDevice.ReCheck, False, "Degrees"),
            ("Range of Motion Knob", RePlayDevice.ReCheck, False, "Degrees"),
            ("Range of Motion Wrist", RePlayDevice.ReCheck, False, "Degrees"),

            ("Isometric Handle", RePlayDevice.ReCheck, True, "Newton cm"),
            ("Isometric Knob", RePlayDevice.ReCheck, True, "Newton cm"),
            ("Isometric Wrist", RePlayDevice.ReCheck, True, "Newton cm"),

            ("Isometric Pinch", RePlayDevice.ReCheck, True, "Grams"),
            ("Isometric Pinch Left", RePlayDevice.ReCheck, True, "Grams"),
            ("Isometric Pinch Flexion", RePlayDevice.ReCheck, True, "Grams"),
            ("Isometric Pinch Extension", RePlayDevice.ReCheck, True, "Grams"),
            ("Isometric Pinch Left Flexion", RePlayDevice.ReCheck, True, "Grams"),
            ("Isometric Pinch Left Extension", RePlayDevice.ReCheck, True, "Grams"),

            #Touchscreen exercises
            ("Touch", RePlayDevice.Touchscreen, False, "Pixels"),

            #Keyboard exercises
            ("Typing", RePlayDevice.Keyboard, False, "Keys"),
            ("Typing (left handed words)", RePlayDevice.Keyboard, False, "Keys"),
            ("Typing (right handed words)", RePlayDevice.Keyboard, False, "Keys"),

            #ReTrieve
            ("ReTrieve", RePlayDevice.ReTrieve, "Unknown"),  

            #FitMi exercises
            ("Touches", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Clapping", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Reach Across", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Reach Out", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Reach Diagonal", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Grip", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Key Pinch", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Finger Tap", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),
            ("Thumb Press", RePlayDevice.FitMi, True, "Loadcell units (~20 grams/value)"),

            ("Flipping", RePlayDevice.FitMi, False, "Degrees"),
            ("Supination", RePlayDevice.FitMi, False, "Degrees"),

            ("Bicep Curls", RePlayDevice.FitMi, False, "Degrees"),
            ("Rolling", RePlayDevice.FitMi, False, "Degrees"),
            ("Shoulder Abduction", RePlayDevice.FitMi, False, "Degrees"),
            ("Shoulder Extension", RePlayDevice.FitMi, False, "Degrees"),
            ("Wrist Deviation", RePlayDevice.FitMi, False, "Degrees"),
            
            ("Finger Twists", RePlayDevice.FitMi, False, "Degrees"),
            ("Flyout", RePlayDevice.FitMi, False, "Degrees"),
            ("Rotate", RePlayDevice.FitMi, False, "Degrees"),
            ("Wrist Flexion", RePlayDevice.FitMi, False, "Degrees"),
            
            ("Lift", RePlayDevice.FitMi, False, "Unknown"),

            ("Generic movement", RePlayDevice.FitMi, False, "Percent of 180 Degrees"),
            ("Generic bidirectional movement", RePlayDevice.FitMi, False, "Percent of 180 Degrees"),

            #Unknown exercise
            ("Unknown", RePlayDevice.Unknown, False, "Unknown")
        ]

        selectable_games = ["All",
            "RepetitionsMode",
            "Breakout",
            "TrafficRacer", 
            "SpaceRunner", 
            "FruitArchery", 
            "FruitNinja", 
            "TyperShark", 
            "ReTrieve", 
            "ReCheck"
        ]

        game_name_color_palette = {
            "RepetitionsMode" : "#E41A1C",
            "Breakout" : "#377EB8", 
            "TrafficRacer" : "#4DAF4A", 
            "SpaceRunner": "#984EA3", 
            "FruitArchery": "#FF7F00", 
            "FruitNinja": "#FFFF33", 
            "TyperShark": "#A65628", 
            "ReTrieve": "#F781BF", 
            "ReCheck": "#999999"
        }

        exercise_category_color_palette = {
            "FitMi Force" : "#FFEC16",
            "FitMi Flip" : "#3D4DB7",
            "FitMi Arm" : "#1093F5",
            "FitMi Twist" : "#00A7F6",
            "FitMi Lift" : "#9C1AB1",
            "FitMi Generic" : "#00BBD5",
            "ReCheck ROM" : "#46AF4A",
            "ReCheck Isometric" : "#F6402C",
            "ReCheck Pinch" : "#FF9800",
            "Touchscreen" : "#795446",
            "Keyboard" : "#9D9D9D",
            "Unknown" : "#000000"
        }

        exercise_name_category_map = {

            "Touches" : "FitMi Force",
            "Clapping" : "FitMi Force",
            "Reach Across" : "FitMi Force",
            "Reach Out" : "FitMi Force",
            "Reach Diagonal" : "FitMi Force",
            "Grip" : "FitMi Force",
            "Key Pinch" : "FitMi Force",
            "Finger Tap" : "FitMi Force",
            "Thumb Press" : "FitMi Force",

            "Flipping" : "FitMi Flip",
            "Supination" : "FitMi Flip",

            "Bicep Curls" : "FitMi Arm",
            "Rolling" : "FitMi Arm",
            "Shoulder Abduction" : "FitMi Arm",
            "Shoulder Extension" : "FitMi Arm",
            "Wrist Deviation" : "FitMi Arm",
            
            "Finger Twists" : "FitMi Twist",
            "Flyout" : "FitMi Twist",
            "Rotate" : "FitMi Twist",
            "Wrist Flexion" : "FitMi Twist",
            
            "Lift" : "FitMi Lift",

            "Generic movement" : "FitMi Generic",
            "Generic bidirectional movement" : "FitMi Generic",

            "Range of Motion Handle" : "ReCheck ROM",
            "Range of Motion Knob" : "ReCheck ROM",
            "Range of Motion Wrist" : "ReCheck ROM",

            "Isometric Handle" : "ReCheck Isometric",
            "Isometric Knob" : "ReCheck Isometric",
            "Isometric Wrist" : "ReCheck Isometric",

            "Isometric Pinch" : "ReCheck Pinch",
            "Isometric Pinch Left" : "ReCheck Pinch",
            "Isometric Pinch Flexion" : "ReCheck Pinch",
            "Isometric Pinch Extension" : "ReCheck Pinch",
            "Isometric Pinch Left Flexion" : "ReCheck Pinch",
            "Isometric Pinch Left Extension" : "ReCheck Pinch",

            "Touch" : "Touchscreen",

            "Typing" : "Keyboard",
            "Typing (left handed words)" : "Keyboard",
            "Typing (right handed words)" : "Keyboard",

            "Unknown" : "Unknown"
        }