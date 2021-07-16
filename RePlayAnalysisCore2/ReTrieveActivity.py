import persistent

import os
import struct
import time
import itertools
import hashlib
import numpy as np
import pandas
import json

from datetime import datetime
from datetime import timedelta
from pathlib import Path

from .RePlayUtilities import convert_datenum

from RePlayAnalysisCore2.ReTrieveDataFile import ReTrieveDataFile
from RePlayAnalysisCore2.TxBDC_Generic_Activity import TxBDC_Generic_Activity

class ReTrieveActivity(TxBDC_Generic_Activity):

    def __init__(self):
        super().__init__()
        self.activity_name = "ReTrieve"
        self.valid_retrieve_activity = False
        self.raw_json_data = None
        self.set_name = None
        self.set_difficulty = None
        self.datafile = None

    def PopulateReTrieveActivity (self, retrieve_datafile_object):
        #Assign the datafile to this activity
        self.datafile = retrieve_datafile_object
        if (isinstance(self.datafile, ReTrieveDataFile)):
            #Copy the json data into the activity
            self.raw_json_data = self.datafile.json_data

            #Before going any further, let's make sure some basic stuff exists in the file,
            #for this file to be considered "valid"
            if (not ("Meta-UID" in self.raw_json_data)):
                self.valid_retrieve_activity = False
                self._p_changed = True
                print("Invalid ReTrieve data file! No UID found.")
                return

            #Pick out some specific variables from the metadata in the json file
            if ("Meta-UID" in self.raw_json_data):
                self.uid = self.raw_json_data["Meta-UID"]
            if ("Meta-Date" in self.raw_json_data):
                self.start_time = datetime.strptime(self.raw_json_data["Meta-Date"], "%Y_%m_%d_%H.%M.%S")
            if ("Meta-Task-Duration" in self.raw_json_data):
                minutes = self.raw_json_data["Meta-Task-Duration"]
                self.duration = minutes * 60
            if ("Meta-Set" in self.raw_json_data):
                self.set_name = self.raw_json_data["Meta-Set"]
            if ("Meta-Set-Difficulty" in self.raw_json_data):
                self.set_difficulty = self.raw_json_data["Meta-Set-Difficulty"]
            
        self.valid_retrieve_activity = True
        self._p_changed = True

    def GetExerciseName(self):
        return self.activity_name

    def GetDifficulty(self):
        return self.set_difficulty

    def GetNormalizedDifficulty(self):
        retrieve_min_difficulty = 0
        retrieve_max_difficulty = 3

        retrieve_normalized_difficulty = (self.set_difficulty) / (retrieve_max_difficulty - retrieve_min_difficulty)
        return retrieve_normalized_difficulty
