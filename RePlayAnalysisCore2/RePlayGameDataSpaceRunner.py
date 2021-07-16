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

class RePlayGameDataSpaceRunner(RePlayGameData):

    def __init__(self):
        super().__init__()

    def DetermineSignal (self, replay_version_code, game_name, exercise_name, gain, sensitivity):
        #The following pseudocode illustrates how RePlay transforms the signal data before saving it
        #in the data file:
        '''
        NormalizedExerciseData = Exercise.CurrentNormalizedValue;
        bool stim = VNS.Determine_VNS_Triggering(DateTime.Now, Exercise.CurrentNormalizedValue);
        '''

        #Create some default values
        self.signal_actual_units = "Unknown"
        self.signal_actual = []

        #RePlay version code 30 is the first version that was used in the Baylor SCI trial.
        if (replay_version_code >= 30) and hasattr(self, "signal"):
            self.signal_actual = Enumerable(self.signal).select(lambda x: ((x * sensitivity) / gain)).to_list()

            #Determine the units for this signal
            exercise_tuple = Enumerable(RePlayExercises.exercises).where(lambda x: x[0] == exercise_name).first_or_default()
            if (exercise_tuple is not None):
                exercise_units = exercise_tuple[3]
                self.signal_actual_units = exercise_units

        #Set a flag indicating that this object has changed
        self._p_changed = True        

    def GetGameSignal (self, use_real_world_units = True):
        result_signal = []
        result_units = "Unknown"
        if (use_real_world_units) and hasattr(self, "signal_actual"):
            result_signal = self.signal_actual
            result_units = self.signal_actual_units
        elif hasattr(self, "signal"):
            result_signal = self.signal
            result_units = "Transformed game units"

        return (result_signal, self.signal_time, result_units)          

    def ReadGameData(self, file_path, file_name, data_start_location):
        self.filepath = file_path
        self.filename = file_name
        self.__data_start_location = data_start_location

        self.start_time = []
        self.game_file_version = []
        self.game_duration = []

        self.signal_timenum = []
        self.signal_time = []
        self.signal = []
        self.signal_timeelapsed = []
        self.signal_binary = []

        self.space1_info = []
        self.space2_info = []
        self.rocket_info = []
        self.space_speed = []

        self.num_coins = []
        self.coin_info = []

        self.num_obstacles = []
        self.obstacle_info = []

        self.current_score = []

        self.endofattempt_time = []
        self.attempt_score = []
        
        #Create lists for rebaselining information
        self.rebaseline_time = []
        self.number_rebaseline_values = []
        self.rebaseline_values = []
        
        #Grab the file size in bytes
        flength = os.stat(self.filename).st_size

        with open(self.filename, 'rb') as f:

            # seek to the position in the file to begin reading trial information
            f.seek(self.__data_start_location)

            try:
                while (f.tell() < flength - 4):
                    packet_type = RePlayDataFileStatic.read_byte_array(f, 'int')

                    #Packet 1 indicates metadata for a session
                    if packet_type == 1:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.start_time.append(convert_datenum(timenum_read))
                        self.game_file_version.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                        self.game_duration.append(RePlayDataFileStatic.read_byte_array(f, 'int'))

                    elif packet_type == 2:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.signal_timenum.append(convert_datenum(timenum_read))
                        self.signal_timeelapsed.append(self.signal_timenum[-1]-self.signal_timenum[0])
                        self.signal_time.append(self.signal_timeelapsed[-1].total_seconds())
                        
                        self.signal.append(RePlayDataFileStatic.read_byte_array(f, 'double'))

                        if self.game_file_version[0] > 1:
                            self.signal_binary.append(RePlayDataFileStatic.read_byte_array(f, 'double'))

                        #save space1 width, height, and space1_x (Obstacle)
                        packet_space1_info = []
                        packet_space1_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                        packet_space1_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                        packet_space1_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                        self.space1_info.append(packet_space1_info)

                        
                        #save space1 width, height, and space1_x (Obstacle)
                        packet_space2_info = []
                        packet_space2_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                        packet_space2_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                        packet_space2_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                        self.space2_info.append(packet_space2_info)

                        #save rocketship width, height, x, y
                        packet_rocket_info = []
                        packet_rocket_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                        packet_rocket_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                        packet_rocket_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                        packet_rocket_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                        self.rocket_info.append(packet_rocket_info)

                        self.space_speed.append(RePlayDataFileStatic.read_byte_array(f, 'int'))

                        num_coins = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.num_coins.append(num_coins)
                        set_coins_info = []
                        for _ in itertools.repeat(None, num_coins):
                            #save coin x, y, width, height
                            ind_coin_info = []
                            if (self.game_file_version[0] >= 3):
                                _ = RePlayDataFileStatic.read_16byte_guid(f)                            
                            ind_coin_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            ind_coin_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            ind_coin_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            ind_coin_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))

                            set_coins_info.append(ind_coin_info)

                        self.coin_info.append(set_coins_info)

                        num_obstacles = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.num_obstacles.append(num_obstacles)
                        set_obs_info = []
                        for _ in itertools.repeat(None, num_obstacles):
                            #save obstacle x, y, width, height
                            ind_obs_info = []
                            if (self.game_file_version[0] >= 3):
                                _ = RePlayDataFileStatic.read_16byte_guid(f)                            
                            ind_obs_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            ind_obs_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            ind_obs_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            ind_obs_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))

                            set_obs_info.append(ind_obs_info)

                        self.obstacle_info.append(set_obs_info)

                        self.current_score.append(RePlayDataFileStatic.read_byte_array(f, 'int'))

                    elif packet_type == 3:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.endofattempt_time.append(convert_datenum(timenum_read))
                        self.attempt_score.append(RePlayDataFileStatic.read_byte_array(f, 'int'))

                    elif packet_type == 4:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.rebaseline_time.append(convert_datenum(timenum_read))

                        number_rebaseline_values = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.number_rebaseline_values.append(number_rebaseline_values)

                        temp_baselines = []
                        for _ in itertools.repeat(None, number_rebaseline_values):
                            temp_baselines.append(RePlayDataFileStatic.read_byte_array(f, 'double'))

                        self.rebaseline_values.append(temp_baselines)

                    elif packet_type == 5:
                        #Start-of-attempt marker packet
                        if (self.game_file_version[0] >= 3):
                            _ = RePlayDataFileStatic.read_byte_array(f, 'float64')

                    elif packet_type == 6:
                        #Coin capture packet
                        if (self.game_file_version[0] >= 3):
                            _ = RePlayDataFileStatic.read_byte_array(f, 'float64')  

                    else:
                        self.bad_packet_count = self.bad_packet_count + 1
                        if (self.bad_packet_count > 10):
                            self.aborted_file = True
                            print("Aborting file because bad packet count exceeded 10 bad packets.")
                            return                                                  

            except:
                print(f'\nGame Crash detected during read of file: {self.filepath.stem}')
                self.crash_detected = 1

        self._p_changed = True

    def CalculateSpaceRunnerMetrics (self):
        #For Space Runner, we will calculate the following metrics:
        #1. The score from each attempt
        #2. The duration of each attempt
        #3. How many attempts occurred
        #4. How each attempt ended (either "0" for death or "1" for timed-out)
        #5. How many coins was the user able to retrieve?

        #1. The score from the best attempt
        #2. The average score from all attempts
        #3. The duration of each attempt
        #4. The duration of the longest attempt
        #5. The number of attempts per session
        #6. The number of attempts per minute

        number_of_attempts = 0
        attempt_scores = []
        attempt_durations = []
        each_attempt_coins = []
        
        #Get the scores from this session and save them in a temporary variable
        attempt_scores = self.attempt_score

        #If no attempt scores were explicitly saved, it's likely there was only 1 attempt, 
        #so let's just get the max score and called that the score for the attempt.
        if (len(attempt_scores) < 1):
            try:
                scores_array = np.array(self.current_score)
                single_attempt_score = np.nanmax(scores_array)
                attempt_scores.append(single_attempt_score)
            except:
                pass

        #Get the duration of each attempt from this session and save it in a temporary variable
        end_of_attempt_times = self.endofattempt_time
        attempt_durations = []
        if (len(end_of_attempt_times) > 1):
            attempt_durations = np.diff(end_of_attempt_times)
            attempt_durations = [x.total_seconds() for x in attempt_durations]
        else:
            try:
                single_attempt_duration = np.nanmax(np.array(self.signal_time))
                attempt_durations.append(single_attempt_duration)
            except:
                pass
        
        #Get the number of attempts that occurred
        number_of_attempts = len(attempt_durations)

        #Create a note of how each attempt ended. Basically, it is "0" for every attempt except the final attempt.
        how_attempts_ended = [0] * number_of_attempts
        how_attempts_ended[-1] = 1

        #Now let's calculate how many coins the user was able to retrieve on each attempt
        score_column = np.array(self.current_score)
        diff_score_column = np.diff(score_column)
        end_of_attempt_indices = np.where(diff_score_column < 0)[0]
        if (len(end_of_attempt_indices) == 0):
            end_of_attempt_indices = [len(diff_score_column) - 1]
        start_of_this_attempt_idx = 0
        end_of_this_attempt_idx = 0
        for i in range(0, len(end_of_attempt_indices)):
            if (i > 0):
                start_of_this_attempt_idx = end_of_this_attempt_idx + 1
            end_of_this_attempt_idx = end_of_attempt_indices[i]
            end_of_list_slice = end_of_this_attempt_idx + 1
            this_attempt_diff_scores = np.array(diff_score_column[start_of_this_attempt_idx:end_of_list_slice])
            number_of_coins = len(np.where(this_attempt_diff_scores > 1)[0])
            each_attempt_coins.append(number_of_coins)

        #Now let's also return a flag indicating whether it seems this session crashed or not
        #If it did crash, we should likely ignore the result of the LAST attempt (the attempt during which the game crashed)
        session_duration = np.nanmax(np.array(self.signal_time))
        crash_flag = False
        if (session_duration < 118):
            #We choose 118 because all sessions should be at least 120 seconds long. 
            #In practice a full session should be longer than 120 if the user had multiple attempts, because the game timer
            #stops inbetween attempts.
            crash_flag = True

        return (number_of_attempts, attempt_scores, attempt_durations, each_attempt_coins, crash_flag)