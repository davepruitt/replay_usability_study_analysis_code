import persistent
import numpy as np

import os
import struct
import time
import itertools
import hashlib
import pandas
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from RePlayAnalysisCore2.RePlaySignalAnalyzer import RePlaySignalAnalyzer

class RePlayGameData(persistent.Persistent):

    #Base constructor
    def __init__(self):
        self.game_data_file_version = 0

    #Empty shell of a function that will be inherited by child classes.
    #This function will tell the analysis code how to convert the signal
    #that was saved in the data file into 2 signals: the signal in 
    #real-world units and the signal in "game units".
    def DetermineSignal (self, replay_version_code, game_name, exercise_name, gain, sensitivity):
        pass

    #Empty shell of a function that will be inherited by child classes. 
    #This method will be used to read in game data for each individual game.
    def ReadGameData(self, file_path, file_name, data_start_location):
        self._p_changed = True

    def GetRepetitionData(self, exercise_name):
        result_rep_start_idx = []
        result_repetition_count = 0
        time_moving = 0
        percent_time_moving = 0

        #Analyze the session data and plot the session signal
        if (hasattr(self, "signal_actual")):

            result_signal_actual = self.signal_actual
            result_signal_timestamps = self.signal_time

            try:
                signal_analyzer = RePlaySignalAnalyzer(
                    exercise_name, 
                    result_signal_actual, 
                    None, 
                    result_signal_timestamps)
                (result_rep_start_idx, _, _, _) = signal_analyzer.CalculateRepetitionTimes()
                (time_moving, percent_time_moving) = signal_analyzer.CalculateTimeSpentMoving()
                result_repetition_count = len(result_rep_start_idx)
            except:
                pass    

        return (result_repetition_count, result_rep_start_idx, time_moving, percent_time_moving)

    def GetGameSignal (self, use_real_world_units = True):
        result_signal = []
        result_units = "Unknown"
        if (use_real_world_units) and hasattr(self, "signal_actual"):
            result_signal = self.signal_actual
        elif hasattr(self, "signal"):
            result_signal = self.signal

        return (result_signal, self.signal_time, result_units)

    def GetDifficulty(self):
        result = 1
        if (hasattr(self, "difficulty")):
            if (isinstance(self.difficulty, list)):
                if (len(self.difficulty) > 0):
                    result = self.difficulty[0]
            else:
                result = self.difficulty        
        return result
        

