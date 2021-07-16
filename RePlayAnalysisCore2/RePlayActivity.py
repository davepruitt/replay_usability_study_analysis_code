from RePlayAnalysisCore2.RePlayControllerData import RePlayControllerData
from RePlayAnalysisCore2.RePlayDataFile import RePlayDataFile
import persistent
import transaction
import math

from datetime import datetime
from datetime import timedelta

from RePlayAnalysisCore2.RePlayGameData import RePlayGameData
from RePlayAnalysisCore2.TxBDC_Generic_Activity import TxBDC_Generic_Activity
from RePlayAnalysisCore2.RePlaySignalAnalyzer import RePlaySignalAnalyzer
from RePlayAnalysisCore2.RePlayGameDataTyperShark import RePlayGameDataTyperShark
from RePlayAnalysisCore2.RePlayVNSAlgorithm import RePlayVNSAlgorithm
from RePlayAnalysisCore2.RePlayVNSAlgorithm_TyperShark import RePlayVNSAlgorithm_TyperShark

class RePlayActivity(TxBDC_Generic_Activity):

    def __init__(self):
        super().__init__()
        self.controller_data = None
        self.game_data = None

    def SetControllerData(self, ctl_data):
        self.controller_data = ctl_data
        self._p_changed = True

    def SetGameData(self, g_data):
        self.game_data = g_data
        self._p_changed = True

    def GetExerciseName(self):
        exercise_name = ""
        if (self.game_data is not None):
            exercise_name = self.game_data.exercise_id     
        return exercise_name

    def GetDifficulty(self):
        result = 1
        if (self.game_data is not None):
            if (self.game_data.game_data is not None):
                result = self.game_data.game_data.GetDifficulty()

        return result

    def GetGain (self):
        result = 1
        if (self.game_data is not None):
            if (hasattr(self.game_data, "gain")):
                result = self.game_data.gain
        elif (self.controller_data is not None):
            if (hasattr(self.controller_data, "gain")):
                result = self.controller_data.gain

        return result

    def GetRepetitionData(self, prefer_metadata = False):
        #Initialize variables that will be used to store the result
        rep_list = []
        rep_count = 0
        time_moving = timedelta(seconds = 0)
        percent_time_moving = 0

        #If the caller prefers to use the pre-calculated metadata, let's grab that...
        if (prefer_metadata) and ("replay_activity_metadata" in self.tags):
            metadata = self.tags["replay_activity_metadata"]
            if ("rep_count" in metadata):
                rep_count = metadata["rep_count"]
            if ("rep_list" in metadata):
                rep_list = metadata["rep_list"]
            if ("time_moving" in metadata):
                time_moving = metadata["time_moving"]
            if ("percent_time_moving" in metadata):
                percent_time_moving = metadata["percent_time_moving"]
        elif (self.game_data is not None):
            #Otherwise, let's do a fresh calculation of the repetition data.
            if (isinstance(self.game_data, RePlayDataFile)):
                if ((self.game_data.game_data is not None) and (isinstance(self.game_data.game_data, RePlayGameData))):
                    #Calculate the repetition data
                    exercise_id = self.game_data.exercise_id
                    (rep_count, rep_list, time_moving, percent_time_moving) = self.game_data.game_data.GetRepetitionData(exercise_id)

                    #Save the calculated data into the metadata for this activity
                    if ("replay_activity_metadata" not in self.tags):
                        self.tags["replay_activity_metadata"] = persistent.mapping.PersistentMapping()
                    self.tags["replay_activity_metadata"]["rep_count"] = rep_count
                    self.tags["replay_activity_metadata"]["rep_list"] = rep_list
                    self.tags["replay_activity_metadata"]["time_moving"] = time_moving
                    self.tags["replay_activity_metadata"]["percent_time_moving"] = percent_time_moving
                    transaction.commit()

        #Return the repetition data to the caller
        return (rep_count, rep_list, time_moving, percent_time_moving)

    def GetGameSignal (self, use_real_world_units = True):
        #Get the game signal from the game data class
        if (self.game_data is not None):
            if (isinstance(self.game_data, RePlayDataFile)):
                if ((self.game_data.game_data is not None) and (isinstance(self.game_data.game_data, RePlayGameData))):
                    return self.game_data.game_data.GetGameSignal(use_real_world_units)
        
        #In the case that the above doesn't work, return some empty arrays
        return ([], [], "")

    def GetVNSSignal (self, custom_parameters = None):
        #(game_signal, game_signal_timestamps) = self.GetGameSignal(False)
        #exercise_name = self.GetExerciseName()
        #signal_analyzer = RePlaySignalAnalyzer(exercise_name, game_signal, None, game_signal_timestamps)
        #processed_signal = signal_analyzer.processed_signal
        #if (processed_signal is None) or (len(processed_signal) != len(game_signal)):
        #    processed_signal = [0] * len(game_signal)
        #return processed_signal

        (game_signal, game_signal_timestamps, _) = self.GetGameSignal(False)
        
        vns_parameters = custom_parameters
        if (custom_parameters is None):
            vns_parameters = self.GetVNSParameters()

        vns_signal = []
        if (self.activity_name == "TyperShark"):
            result = []
            for i in range(0, len(game_signal)):
                if (game_signal[i] > 0):
                    result.append(game_signal_timestamps[i])
            vns_signal = RePlayVNSAlgorithm_TyperShark.ProcessSignal(result, vns_parameters)
        else:
            vns_signal = RePlayVNSAlgorithm.ProcessSignal(game_signal, game_signal_timestamps, vns_parameters)
        return vns_signal

    def GetVNSParameters (self):
        #If the game data file has a "vns_algorithm_parameters" object, return that object
        if (self.game_data is not None):
            if (isinstance(self.game_data, RePlayDataFile)):
                if (hasattr(self.game_data, "vns_algorithm_parameters")):
                    return self.game_data.vns_algorithm_parameters

        #Otherwise, if the controller data file has a "vns_algorithm_parameters" object, return that object
        if (self.controller_data is not None):
            if (isinstance(self.controller_data, RePlayDataFile)):
                if (hasattr(self.controller_data, "vns_algorithm_parameters")):
                    return self.controller_data.vns_algorithm_parameters
        
        #Otherwise, just return null
        return None

    def GetRePlayStimulationRequests (self):
        result = []
        try:
            is_typershark = False
            if (self.game_data is not None):
                if (self.game_data.game_data is not None) and (isinstance(self.game_data.game_data, RePlayGameDataTyperShark)):
                    is_typershark = True
                    for i in range(0, len(self.stimulation_occur)):
                        if (self.stimulation_occur[i] > 0):
                            result.append(self.signal_timenum[i])
            if (not is_typershark):
                if (self.controller_data is not None) and (isinstance(self.controller_data, RePlayDataFile)):
                    if (self.controller_data.controller_data is not None) and (isinstance(self.controller_data.controller_data, RePlayControllerData)):
                        controller_data = self.controller_data.controller_data
                        result = controller_data.stim_times
        except:
            pass

        return result

    def GetRePlayStimulationRecords (self):
        result = []
        try:
            is_typershark = False
            if (self.game_data is not None):
                if (self.game_data.game_data is not None) and (isinstance(self.game_data.game_data, RePlayGameDataTyperShark)):
                    is_typershark = True
                    if (hasattr(self.game_data.game_data, "stim_times_successful")):
                        result = self.game_data.game_data.stim_times_successful
            if (not is_typershark):
                if (self.controller_data is not None) and (isinstance(self.controller_data, RePlayDataFile)):
                    if (self.controller_data.controller_data is not None) and (isinstance(self.controller_data.controller_data, RePlayControllerData)):
                        controller_data = self.controller_data.controller_data
                        result = controller_data.stim_times_successful
        except:
            pass

        return result
        

    #region Static methods

    @staticmethod
    def AddSessionToActivityList(activity_list, session_data):
        #Grab the participant ID and the start time of the session
        participant_id = session_data.subject_id
        activity_name = session_data.game_id
        session_start_time = session_data.session_start
        file_name = session_data.filepath.name

        #Generate the table names for this data file
        is_gamedata_file = session_data.data_type
        
        #Figure out the duration of the session
        session_duration = float("nan")
        if ((is_gamedata_file) and 
            (hasattr(session_data, "game_data")) and 
            (hasattr(session_data.game_data, "signal_time")) and
            (len(session_data.game_data.signal_time) > 0)):

            #Grab the last element of the "signal time" array
            #This should be essentially how long the session was
            session_duration = session_data.game_data.signal_time[-1]

        elif ((hasattr(session_data, "controller_data")) and 
            (hasattr(session_data.controller_data, "signal_time")) and
            (len(session_data.controller_data.signal_time) > 0)):

            #Grab the last element of the "signal time" array
            #This should be essentially how long the session was
            session_duration = session_data.controller_data.signal_time[-1]
        
        #Now let's see if there is already a row in the database that
        #we can just update, or let's see if we need to create a new
        #row in the database.
        time_allowance = 5
        found = False

        #Iterate over all existing activities in the activity list
        for i in range(0, len(activity_list)):
            cur_activity = activity_list[i]

            #Check to see if the UID and activity name match
            if ((cur_activity.uid == participant_id) and (cur_activity.activity_name == activity_name)):
                cur_start = cur_activity.start_time
                time_delta = session_start_time - cur_start
                time_delta_total_seconds = abs(time_delta.total_seconds())
                if (time_delta_total_seconds <= time_allowance):
                    found = True

                    if ((math.isnan(cur_activity.duration)) or 
                        (is_gamedata_file and not math.isnan(session_duration))):

                        cur_activity.duration = session_duration

                    if (is_gamedata_file and (cur_activity.game_data is None)):
                        cur_activity.SetGameData(session_data)
                    else:
                        if (cur_activity.controller_data is None):
                            cur_activity.SetControllerData(session_data)

        #If we did not find any records that matched the criteria for "updating",
        #then we should INSERT a new record into the list
        if not found:
            new_activity = RePlayActivity()
            new_activity.uid = participant_id
            new_activity.activity_name = activity_name
            new_activity.start_time = session_start_time
            new_activity.duration = session_duration

            if (is_gamedata_file):
                new_activity.SetGameData(session_data)
            else:
                new_activity.SetControllerData(session_data)

            activity_list.append(new_activity)
    
    #endregion

                    
        
