import json
import os.path
from os import path

from pathlib import Path

from tkinter import filedialog
from tkinter import Tk

from .RePlayGUI import RePlayGUI

#This class is meant to handle any configuration details that the analysis code needs to deal with
class RePlayAnalysisConfiguration:

    #Static variables

    analysis_configuration_path = "./Unversioned_Assets/"
    analysis_configuration_file = "analysis_configuration.json"

    database_location = None
    control_database_location = None
    box_folder_location = None
    retrieve_pkl_location = None
    figure_saving_location = None

    #Static methods

    #This method is meant to write all necessary variables to the configuration file
    @staticmethod
    def WriteConfigurationFile ():
        json_dictionary = {
            "database_location" : RePlayAnalysisConfiguration.database_location,
            "box_folder_location" : RePlayAnalysisConfiguration.box_folder_location,
            "retrieve_pkl_location" : RePlayAnalysisConfiguration.retrieve_pkl_location,
            "figure_saving_location" : RePlayAnalysisConfiguration.figure_saving_location,
            "control_database_location" : RePlayAnalysisConfiguration.control_database_location
        }

        Path(RePlayAnalysisConfiguration.analysis_configuration_path).mkdir(parents=True, exist_ok=True)
        full_path = RePlayAnalysisConfiguration.analysis_configuration_path + RePlayAnalysisConfiguration.analysis_configuration_file
        with open(full_path, 'w') as json_file:
            json.dump(json_dictionary, json_file, sort_keys=True, indent=4, separators=(',', ': '))

    #This method is meant to read in the variables from the configuration file so they can be used
    @staticmethod
    def ReadConfigurationFile(request_if_not_found : bool = False):
        #Check to see if the configuration file exists. If it does, read it in
        full_path = RePlayAnalysisConfiguration.analysis_configuration_path + RePlayAnalysisConfiguration.analysis_configuration_file
        if (path.exists(full_path)):
            with open(full_path) as json_file:
                json_data = json.load(json_file)

                try:
                    RePlayAnalysisConfiguration.database_location = json_data["database_location"]
                except KeyError:
                    pass
                
                try:
                    RePlayAnalysisConfiguration.box_folder_location = json_data["box_folder_location"]
                except KeyError:
                    pass

                try:
                    RePlayAnalysisConfiguration.retrieve_pkl_location = json_data["retrieve_pkl_location"]
                except KeyError:
                    pass

                try:
                    RePlayAnalysisConfiguration.figure_saving_location = json_data["figure_saving_location"]
                except KeyError:
                    pass

                try:
                    RePlayAnalysisConfiguration.control_database_location = json_data["control_database_location"]
                except KeyError:
                    pass
        
        #Now, if the "request_if_not_found" flag is set to "True", then request that the user
        #manually give some values if the configuration file did not contain them
        if (request_if_not_found):
            if not RePlayAnalysisConfiguration.database_location:

                #Ask the user if they would like to show the program where the existing database is
                #located, OR if they would like to create a new database from scratch
                result = RePlayGUI.ask("Database question", 
                    "We don't know where the database is located! " \
                    "Would you like to create a new database, or show us where the existing datbase is?", 
                    ("New database", "Find existing database"))
                if (result == "New database"):
                    file_name = filedialog.asksaveasfilename(title = "Choose a filename for the new database", 
                        filetypes = [("SQLite Databases", ".db")], defaultextension = ".db")
                else:
                    file_name = filedialog.askopenfilename(title = "Please select the database file")

                RePlayAnalysisConfiguration.database_location = file_name

            if not RePlayAnalysisConfiguration.control_database_location:

                result = RePlayGUI.ask("Control database question",
                "We don't know where the CONTROL database is located! " \
                "Would you like to create a new database, or show us where the existing database is?",
                ("New database", "Find existing database"))

                if (result == "New database"):
                    file_name = filedialog.asksaveasfilename(title = "Choose a filename for the new database", 
                        filetypes = [("SQLite Databases", ".db")], defaultextension = ".db")
                else:
                    file_name = filedialog.askopenfilename(title = "Please select the database file")

                RePlayAnalysisConfiguration.control_database_location = file_name
            
            if not RePlayAnalysisConfiguration.box_folder_location:
                folder_name = filedialog.askdirectory(title = "Please select the location of the Box folder")
                RePlayAnalysisConfiguration.box_folder_location = folder_name

            if not RePlayAnalysisConfiguration.retrieve_pkl_location:
                folder_name = filedialog.askdirectory(title = "Please select the location of the ReTrieve PKL files")
                RePlayAnalysisConfiguration.retrieve_pkl_location = folder_name

            if not RePlayAnalysisConfiguration.figure_saving_location:
                folder_name = filedialog.askdirectory(title = "Where do you plan on saving your figures?")
                RePlayAnalysisConfiguration.figure_saving_location = folder_name

            #Now that we have updated values selected by the user, let's update the configuration file
            #with these new values
            RePlayAnalysisConfiguration.WriteConfigurationFile()