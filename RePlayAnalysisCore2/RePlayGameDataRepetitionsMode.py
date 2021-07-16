import os
import struct
import time
import itertools
import hashlib
import numpy as np
import pandas
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from py_linq import Enumerable

from .RePlayUtilities import convert_datenum
from .RePlayGameData import RePlayGameData
from .RePlayDataFileStatic import RePlayDataFileStatic
from .RePlayExercises import RePlayExercises
from .RePlayExercises import RePlayDevice

class RePlayGameDataRepetitionsMode(RePlayGameData):

    def __init__(self):
        super().__init__()

    def DetermineSignal (self, replay_version_code, game_name, exercise_name, gain, sensitivity):
        #Create some default values
        self.signal_actual_units = "Unknown"
        self.signal_actual = []
        self.signal_transformed = []

        exercise_tuple = Enumerable(RePlayExercises.exercises).where(lambda x: x[0] == exercise_name).first_or_default()

        #RePlay version code 30 is the first version that was used in the Baylor SCI trial.
        if (exercise_tuple is not None) and hasattr(self, "signal_not_normalized"):
            is_force_exercise = exercise_tuple[2]
            device_used = exercise_tuple[1]

            #Set the value of signal actual and its units
            self.signal_actual = self.signal_not_normalized
            self.signal_actual_units = exercise_tuple[3]            

            #Now calculate the game signal
            debounce_list = []
            for s in self.signal_not_normalized:
                val = 0
                if game_name == "ReCheck":
                    debounce_list.append(s)
                    debounce_list = debounce_list[-10:]

                    if (len(debounce_list) >= 10):
                        if is_force_exercise:
                            val = np.nanmedian(debounce_list)
                        else:
                            val = np.nanmean(np.diff(debounce_list))
                else:
                    if device_used == RePlayDevice.ReCheck:
                        debounce_list.append(s * gain)
                    else:
                        debounce_list.append(s * gain / sensitivity)
                    debounce_list = debounce_list[-10:]
                    
                    if (len(debounce_list) >= 10):
                        if (exercise_name == "Flipping") or (exercise_name == "Supination"):
                            val = np.nanmean(np.diff(debounce_list))
                        else:
                            val = np.nanmedian(debounce_list)

                self.signal_transformed.append(val)

        #Set a flag indicating that this object has changed
        self._p_changed = True          

    def GetGameSignal (self, use_real_world_units = True):
        if hasattr(self, "signal_actual") and hasattr(self, "signal_transformed"):
            result_signal = []
            result_units = "Unknown"
            
            if (use_real_world_units):
                result_signal = self.signal_actual
                result_units = self.signal_actual_units
            else:
                result_signal = self.signal_transformed
                result_units = "Transformed game units"

            return (result_signal, self.signal_time, result_units)
        else:
            return super().GetGameSignal(use_real_world_units)

    def ReadGameData(self, file_path, file_name, data_start_location):
        self.filepath = file_path
        self.filename = file_name
        self.__data_start_location = data_start_location

        self.start_time = []
        self.rep_start_time = []
        self.hit_threshold = []
        self.signal = []
        self.signal_not_normalized = []
        self.signal_time = []
        self.signal_timenum = []
        self.signal_timeelapsed = []
        self.is_session_handedness_known = False
        self.is_session_left_handed = False        

        rep_values= []
        rep_timestamps = []
        rep_timeelapsed = []
        rep_time = []

        self.end_of_attempt_time = []

        #Initialize the game file version to a default value
        self.game_file_version = 1
        
        #Create lists for rebaselining information
        self.rebaseline_time = []
        self.number_rebaseline_values = []
        self.rebaseline_values = []

        #Grab the file size in bytes
        flength = os.stat(self.filename).st_size

        with open(self.filename, 'rb') as f:

            f.seek(self.__data_start_location)
            try:
                #Modify this line when the replay games call the CloseFile method in the RepModeSaveGameData class
                while (f.tell() < flength - 8):

                    packet_type = RePlayDataFileStatic.read_byte_array(f, 'int')

                    #Packet 1 indicates metadata for a session
                    if packet_type == 1:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.start_time.append(convert_datenum(timenum_read))
                        self.game_file_version = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.target_rep_count = RePlayDataFileStatic.read_byte_array(f, 'int')
                        
                        temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                        self.threshold_type = f.read(temp_length).decode()

                        #Exercise sensitivity was only saved in replay V1, however it was always 1
                        if self.game_file_version == 1:
                            temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                            # self.exercise_sensitivity = f.read(temp_length).decode()
                            _ = f.read(temp_length).decode()
                        
                        self.return_threshold = RePlayDataFileStatic.read_byte_array(f, 'double')
                        self.minimum_trial_duration = RePlayDataFileStatic.read_byte_array(f, 'double')

                        if self.game_file_version >= 4:
                            self.starting_hit_threshold = RePlayDataFileStatic.read_byte_array(f, 'double')
                            self.should_convert_signal_to_velocity = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                            self.is_single_polarity = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                            self.should_force_alternation = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                        else:
                            self.starting_hit_threshold = float("NaN")
                            self.should_convert_signal_to_velocity = -1
                            self.is_single_polarity = -1
                            self.should_force_alternation = -1

                    #Packet 2 indicates gamedata packet
                    elif packet_type == 2:
                        if self.game_file_version >= 5:
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            self.signal_timenum.append(convert_datenum(timenum_read))
                            self.signal_timeelapsed.append(self.signal_timenum[-1]-self.signal_timenum[0])
                            self.signal_time.append(self.signal_timeelapsed[-1].total_seconds())

                            self.signal.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                            self.signal_not_normalized.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                        elif self.game_file_version >= 3:
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            self.signal_timenum.append(convert_datenum(timenum_read))
                            self.signal_timeelapsed.append(self.signal_timenum[-1]-self.signal_timenum[0])
                            self.signal_time.append(self.signal_timeelapsed[-1].total_seconds())

                            self.signal.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                        else:
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            rep_timestamps.append(convert_datenum(timenum_read))
                            rep_timeelapsed.append(rep_timestamps[-1]-rep_timestamps[0])
                            rep_time.append(rep_timeelapsed[-1].total_seconds())

                            temp_read = RePlayDataFileStatic.read_byte_array(f, 'double')
                            rep_values.append(temp_read)

                    #Packet 3 indiciates rephead data
                    elif packet_type == 3:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.rep_start_time.append(convert_datenum(timenum_read))
                        self.hit_threshold.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                        
                        #In game file versions 1 and 2, the data was saved to the game data file as individual repetitions.
                        #Therefore, we simply must reconstruct the signal from each of these individual repetitions.
                        if self.game_file_version < 3:
                            if len(rep_values) > 0:
                                inter_rep_interval = 0
                                if (len(self.end_of_attempt_time) > 0):
                                    temp_isi = rep_timestamps[0] - self.end_of_attempt_time[-1]
                                    inter_rep_interval = temp_isi.total_seconds()

                                base_time_addon = inter_rep_interval
                                if (len(self.signal_time) > 0):
                                    base_time_addon = self.signal_time[-1] + inter_rep_interval
                                base_time_addon_timedelta = timedelta(seconds = base_time_addon)

                                rep_time = [(x + base_time_addon) for x in rep_time]
                                rep_timeelapsed = [(x + base_time_addon_timedelta) for x in rep_timeelapsed]

                                self.signal.extend(rep_values)
                                self.signal_timenum.extend(rep_timestamps)
                                self.signal_timeelapsed.extend(rep_timeelapsed)
                                self.signal_time.extend(rep_time)
                                self.end_of_attempt_time.append(rep_timestamps[-1])
                                
                            rep_values = []
                            rep_timestamps = []
                            rep_timeelapsed = []
                            rep_time = []

                    #Packet 4 indiciates rebaseline packet
                    elif packet_type == 4:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.rebaseline_time.append(convert_datenum(timenum_read))

                        number_rebaseline_values = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.number_rebaseline_values.append(number_rebaseline_values)

                        temp_baselines = []
                        for _ in itertools.repeat(None, number_rebaseline_values):
                            temp_baselines.append(RePlayDataFileStatic.read_byte_array(f, 'double'))

                        self.rebaseline_values.append(temp_baselines)

                    #Packet 5 indicates end of attempt packet 
                    elif packet_type == 5:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.end_of_attempt_time.append(convert_datenum(timenum_read))

                    #Packet 6 indicates the "handedness" of the session
                    elif packet_type == 6:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        is_left_handed_int8 = RePlayDataFileStatic.read_byte_array(f, 'int8')
                        self.is_session_handedness_known = True
                        self.is_session_left_handed = False
                        if (is_left_handed_int8 == 1):
                            self.is_session_left_handed = True
                        
                    else:
                        self.bad_packet_count = self.bad_packet_count + 1
                        if (self.bad_packet_count > 10):
                            self.aborted_file = True
                            print("Aborting file because bad packet count exceeded 10 bad packets.")
                            return

            except:
                print(f'\nGame Crash detected during read of file: {self.filepath.stem}')
                self.crash_detected = 1

        #Final clean-up work. This is necessary to catch the last data in the file that is not properly
        #handled in the if-else statement above (for game file versions < 3).
        if self.game_file_version < 3:
            if len(rep_values) > 0:
                inter_rep_interval = 0
                if (len(self.end_of_attempt_time) > 0):
                    temp_isi = rep_timestamps[0] - self.end_of_attempt_time[-1]
                    inter_rep_interval = temp_isi.total_seconds()

                base_time_addon = inter_rep_interval
                if (len(self.signal_time) > 0):
                    base_time_addon = self.signal_time[-1] + inter_rep_interval
                base_time_addon_timedelta = timedelta(seconds = base_time_addon)

                rep_time = [(x + base_time_addon) for x in rep_time]
                rep_timeelapsed = [(x + base_time_addon_timedelta) for x in rep_timeelapsed]                

                self.signal.extend(rep_values)
                self.signal_timenum.extend(rep_timestamps)
                self.signal_timeelapsed.extend(rep_timeelapsed)
                self.signal_time.extend(rep_time)
                self.end_of_attempt_time.append(rep_timestamps[-1])

        self._p_changed = True

    def GetRepetitionData(self, exercise_name):
        result_rep_start_idx = []
        result_repetition_count = 0
        result_time_moving = timedelta(seconds=0)
        result_percent_time_moving = 0

        if (hasattr(self, "signal_actual")):
            if (len(self.rep_start_time) > 0):
                result_repetition_count = len(self.rep_start_time)

                #Find the sample index at which each rep began
                for i in range(0, len(self.rep_start_time)):
                    current_rep_start_time = self.rep_start_time[i]
                    try:
                        idx = next(x[0] for x in enumerate(self.signal_timenum) if x[1] >= current_rep_start_time)
                        result_rep_start_idx.append(idx)

                        (_, _, result_time_moving, result_percent_time_moving) = super().GetRepetitionData(exercise_name)
                    except:
                        continue

        return (result_repetition_count, result_rep_start_idx, result_time_moving, result_percent_time_moving)
        
    def GetDifficulty(self):
        result = 1
        if (hasattr(self, "target_rep_count")):
            result = self.target_rep_count
        return result
        
