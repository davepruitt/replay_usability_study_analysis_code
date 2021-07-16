from tkinter import filedialog
from tkinter import Tk
from tkinter import dialog

#This class is meant to handle any basic GUI functionality that the analysis code
#may need, such as displaying a pop-up.
class RePlayGUI:

    #region Static variables

    root_window = None

    #endregion
    
    #region Static methods

    @staticmethod
    def InitializeGUI ():
        #Create the root window and then make it disappear
        RePlayGUI.root_window = Tk()
        RePlayGUI.root_window.withdraw()

    @staticmethod
    def ask(title, text, strings=('Yes', 'No'), bitmap='questhead', default=0):

        #Initialize the GUI if it has not already been done
        if (not RePlayGUI.root_window):
            RePlayGUI.InitializeGUI()

        #Create the dialog box
        d = dialog.Dialog(
            title=title, text=text, bitmap=bitmap, default=default, strings=strings)
        return strings[d.num]
    
    #endregion
