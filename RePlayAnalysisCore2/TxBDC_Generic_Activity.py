from RePlayAnalysisCore2.RePlayDataFile import RePlayDataFile
import persistent
import math

from datetime import datetime
from datetime import timedelta

from py_linq import Enumerable

from RePlayAnalysisCore2.RePlayGameData import RePlayGameData
from RePlayAnalysisCore2 import RePlayUtilities

class TxBDC_Generic_Activity(persistent.Persistent):

    def __init__(self):
        self.uid = None
        self.activity_name = None
        self.start_time = None
        self.duration = None
        self.parent_visit = None
        self.tags = persistent.mapping.PersistentMapping()

    def GetExerciseName(self):
        return ""

    def GetDifficulty(self):
        return 1

    def GetNormalizedDifficulty(self):
        return float("NaN")

    def GetGain(self):
        return float("NaN")        

    def GetStimulationsFromReStoreDatalogs(self):
        stims_during_this_activity = []
        current_activity_starttime = self.start_time
        current_activity_endtime = current_activity_starttime + timedelta(seconds = self.duration)
        current_visit = self.parent_visit
        if (current_visit is not None):
            current_participant = current_visit.parent_participant
            if (current_participant is not None) and ("restore_data" in current_participant.tags):
                all_stims_for_this_participant = current_participant.tags["restore_data"]
                all_stim_datetimes = Enumerable(all_stims_for_this_participant).select(lambda x: RePlayUtilities.convert_restore_event_to_datetime(x["START_TIME"], x["EVENT_START"])).to_list()
                stims_during_this_activity = Enumerable(all_stim_datetimes).where(lambda x: ((x >= current_activity_starttime) and (x <= current_activity_endtime))).to_list()
        
        return stims_during_this_activity

