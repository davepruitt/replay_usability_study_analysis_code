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
import math

from .RePlayUtilities import convert_datenum
from .RePlayGameData import RePlayGameData
from .RePlayDataFileStatic import RePlayDataFileStatic

class RePlayGameDataTyperShark(RePlayGameData):

    def __init__(self, version):
        super().__init__()
        self.version = version

    def ReadGameData(self, file_path, file_name, data_start_location):

        self.filepath = file_path
        self.filename = file_name
        self.__data_start_location = data_start_location

        self.signal_time = []
        self.signal_timenum = []
        self.signal_timeelapsed = []
        self.signal_time = []

        self.current_stage_index = []
        self.stage_type = []

        self.shark_guids = []
        self.shark_info = []

        self.num_sharks_stage = []
        self.num_sharks_alive = []

        self.selected_shark_guid = []
        self.num_keys_released = []
        self.key_released_strings = []

        self.stimulation_occur = []

        self.restore_messages = []
        self.stim_times_successful = []

        #Grab the file size in bytes
        flength = os.stat(self.filename).st_size

        with open(self.filename, 'rb') as f:

            # seek to the position in the file to begin reading trial information
            f.seek(self.__data_start_location)

            try:
                while (f.tell() < flength - 4):
                    #Check to see what kind of packet we are dealing with
                    packet_type = RePlayDataFileStatic.read_byte_array(f, 'int')
                    
                    if (self.version <= 7):
                        #If the file version is less than or equal to 7, there is a bug that we must account for.
                        #The code saves out a "2" identifier, indicating that there is a game data packet coming
                        #up next in the file, but sometimes there may not be a game data packet if the game was
                        #in a certain state. Luckily, the "2" identifier is the only packet identifier in these
                        #earlier versions, so we don't have to worry about distinguishing this from any other 
                        #kind of packet. Therefore, once we find a 4-byte segment that is NOT 2, then we know
                        #that we have actually entered a true game data packet. The reason is that the FIRST
                        #thing saved in a game data packet is the TIMESTAMP. The timestamp will always be an
                        #8-byte sequence, and it will NEVER be something as low as 2. So we are guaranteed
                        #that once we find a 4-byte sequence that is NOT 2, we can safely start there and read
                        #in a game data packet.

                        if (packet_type != 2):
                            #Set the correct packet type
                            packet_type = 2
                            is_actual_packet = 1

                            #Now seek back 4 bytes (at the beginning of the previous int read) 
                            #so we can read the full 8 byte timestamp.
                            f.seek(-4, 1)
                        else:
                            #Just loop back around and read the next 4 bytes
                            continue
                    else:
                        #No action is necessary at this point if the file version is 8 or greater.
                        pass

                    #For packet type 2 (a game data packet):
                    if packet_type == 2:
                        
                        is_actual_packet = 0
                        if (self.version >= 8):
                            #If the file version is 8 or greater, than the first byte after the 4-byte packet
                            #identifier will be a true/false value indicating whether this is an actual game
                            #data packet. So let's read that in:
                            is_actual_packet = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                        else:
                            is_actual_packet = 1

                        if is_actual_packet:
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            try:
                                self.signal_timenum.append(convert_datenum(timenum_read))
                            except:
                                print("TyperShark: Unable to convert float64 to datenum")
                                self.signal_timenum.append(float("NaN"))
                            self.signal_timeelapsed.append(self.signal_timenum[-1]-self.signal_timenum[0])

                            try:
                                self.signal_time.append(self.signal_timeelapsed[-1].total_seconds())
                            except:
                                self.signal_time.append(0)

                            self.current_stage_index.append(RePlayDataFileStatic.read_byte_array(f, 'int32'))

                            # Read in the stage type string
                            temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                            self.stage_type.append(f.read(temp_length).decode())

                            self.num_sharks_stage.append(RePlayDataFileStatic.read_byte_array(f, 'int32'))

                            num_sharks_alive = RePlayDataFileStatic.read_byte_array(f, 'int32')
                            self.num_sharks_alive.append(num_sharks_alive)

                            set_shark_info = []

                            for _ in itertools.repeat(None, num_sharks_alive):
                                ind_shark_info = []

                                shark_guid = []
                                for _ in itertools.repeat(None, 16):
                                    shark_guid.append(RePlayDataFileStatic.read_byte_array(f, 'uint8'))
                                

                                #Save the GUID (Global Unique ID) for the shark
                                ind_shark_info.append(shark_guid)

                                #If data for this shark GUID has not been read, then read it in
                                if shark_guid not in self.shark_guids:
                                    
                                    #add this shark GUID to the master GUID list
                                    self.shark_guids.append(shark_guid)

                                    shark_guid_info = []

                                    # Read in the type of shark string
                                    temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                                    shark_guid_info.append(f.read(temp_length).decode())

                                    # Read in the number of words for this shark
                                    num_words = RePlayDataFileStatic.read_byte_array(f, 'int32')
                                    shark_guid_info.append(num_words)

                                    word = []
                                    #Read in the words for this shark
                                    for _ in itertools.repeat(None, num_words):
                                        temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                                        word.append(f.read(temp_length).decode())

                                    shark_guid_info.append(word)

                                    ind_shark_info.append(shark_guid_info)
                                
                                else:
                                    ind_shark_info.append(None)


                                #Save current word index
                                ind_shark_info.append(RePlayDataFileStatic.read_byte_array(f, 'int32'))

                                #Save current character index (which character of the current word)
                                ind_shark_info.append(RePlayDataFileStatic.read_byte_array(f, 'int32'))

                                #Save the current position_x, position_y, velocity_x, velocity_y
                                ind_shark_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                ind_shark_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                ind_shark_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                ind_shark_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))

                                set_shark_info.append(ind_shark_info)

                            #add the shark info to the list
                            self.shark_info.append(set_shark_info)

                            #Read in a bool if a shark is currently selected
                            read_byte = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                            if read_byte == 1:
                                selected_shark_guid = []
                                for _ in itertools.repeat(None, 16):
                                    selected_shark_guid.append(RePlayDataFileStatic.read_byte_array(f, 'uint8'))
                                self.selected_shark_guid.append(selected_shark_guid)

                            else:
                                self.selected_shark_guid.append(None)

                            num_keys_released = RePlayDataFileStatic.read_byte_array(f, 'int')
                            self.num_keys_released.append(num_keys_released)

                            key_released_string = []
                            for _ in itertools.repeat(None, num_keys_released):
                                # Read in the key press string
                                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                                key_released_string.append(f.read(temp_length).decode())

                            self.key_released_strings.append(key_released_string)

                            self.stimulation_occur.append(RePlayDataFileStatic.read_byte_array(f, 'uint8'))
                    elif packet_type == 3:
                        #This code handles reading in a "ReStore Service Message" packet.
                        restore_msg = RePlayDataFileStatic.read_restore_message(f)
                        self.restore_messages.append(restore_msg)
                        if (("secondary" in restore_msg) and ("time" in restore_msg)):
                            time = restore_msg["time"]
                            secondary = restore_msg["secondary"]
                            if ("COMMAND_STATUS" in secondary):
                                is_stim_success = secondary["COMMAND_STATUS"]
                                if (is_stim_success == "STIM_SUCCESS"):
                                    self.stim_times_successful.append(time)                        

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

    def GetRepetitionData(self, exercise_name):
        result_total_reps = 0
        result_rep_idx = []
        result_time_spent_moving = 0
        result_percent_time_moving = 0

        if (self.signal_time is not None) and (len(self.signal_time) > 0):

            num_keys_released = np.array(self.num_keys_released)
            result_rep_idx = np.flatnonzero(num_keys_released > 0)
            result_total_reps = len(result_rep_idx)

            #Calculate a metric for "time spent moving"
            #We will consider each keypress to have 0.5 seconds of movement before and 0.5 second of movement after
            temp_movement_array = np.zeros(len(self.signal_time))

            for i in range(0, len(result_rep_idx)):
                signal_time_idx = result_rep_idx[i]
                keypress_signal_time = self.signal_time[signal_time_idx]
                keypress_start_time = keypress_signal_time - 0.5
                keypress_finish_time = keypress_signal_time + 0.5

                try:
                    keypress_start_idx = next(x[0] for x in enumerate(self.signal_time) if x[1] >= keypress_start_time)
                except:
                    keypress_start_idx = signal_time_idx

                try:
                    keypress_end_idx = next(x[0] for x in enumerate(self.signal_time) if x[1] >= keypress_finish_time)
                except:
                    keypress_end_idx = signal_time_idx

                for j in range(keypress_start_idx, keypress_end_idx):
                    temp_movement_array[j] = 1

            temp_sum = np.nansum(temp_movement_array)
            result_time_spent_moving = (temp_sum / len(self.signal_time)) * self.signal_time[-1]

            #Now calculate the proportion of time spent moving
            try:
                if (self.signal_time[-1] < 0.1):
                    result_percent_time_moving = 0
                else:
                    result_percent_time_moving = (result_time_spent_moving / self.signal_time[-1]) * 100.0
            except:
                result_percent_time_moving = 0
        
        return (result_total_reps, result_rep_idx, timedelta(seconds = result_time_spent_moving), result_percent_time_moving)

    def GetGameSignal(self, use_real_world_units = True):
        return (self.ConvertKeypressSignalToBinary(), self.signal_time, "Keypresses")

    def GetNormalizedDifficulty(self):        
        replay_minimum_difficulty = 1
        replay_maximum_difficulty = 10

        replay_normalized_difficulty = (self.GetDifficulty()) / (replay_maximum_difficulty - replay_minimum_difficulty)
        return replay_normalized_difficulty

    #The purpose of this method is to calclate what the "expected" keypress is at any timepoint
    #during the session. The input to this method is a Pandas dataframe representing the SQL data
    #table of a TyperShark session. The output of this method is a list, equal in size to the number
    #of rows of the dataframe, that contains the value of the "expected keypress" at each timepoint.
    def CalculateExpectedKeypresses (self):

        #Create an empty array that will hold an expected keypress for each timepoint. This will
        #be the result that we return to the caller of this function.
        all_expected_keypresses = []

        #Create a set of unique sharks, where the shark's guid is the key. This set is initially
        #empty, but will be updated throughout this function.
        sharks = {}

        #Iterate over each row of the table (in other words, each timepoint of the session)
        for idx in range(0, len(self.signal_time)):
            #Get the stage type at the current timepoint
            current_stage_type = self.stage_type[idx]

            #Grab the currently active sharks
            current_active_sharks = self.shark_info[idx]

            #Iterate over all sharks that are currently alive to grab updated information
            num_sharks_alive = self.num_sharks_alive[idx]
            alive_shark_guids = []
            for s in range(num_sharks_alive):
                this_shark_info = self.shark_info[idx][s]
                this_shark_guid = str(this_shark_info[0])
                alive_shark_guids.append(this_shark_guid)

                #Check to see if this shark is brand new
                this_shark_newsharkdata = this_shark_info[1]
    
                #If this is a new shark, add it to the set of all sharks
                if this_shark_newsharkdata is not None:
                    sharks[this_shark_guid] = {
                        "shark_data" : this_shark_newsharkdata,
                        "cur_word_idx" : 0,
                        "cur_letter_idx" : 0,
                        "updated_word_idx" : 0,
                        "updated_letter_idx" : 0,
                        "shark_killed" : False
                    }

                #Now let's grab the updated word/letter idx (that take effect AFTER this frame)
                this_shark_updated_word_idx = this_shark_info[2]
                this_shark_updated_letter_idx = this_shark_info[3]
                
                #Set the current word/letter indices for this shark
                sharks[this_shark_guid]["updated_word_idx"] = int(this_shark_updated_word_idx)
                sharks[this_shark_guid]["updated_letter_idx"] = int(this_shark_updated_letter_idx)
  
            #Now let's see which shark is selected, which word we are on, and which letter we are on
            selected_shark_guid_raw = self.selected_shark_guid[idx]
            selected_shark_guid = None
            if selected_shark_guid_raw is not None:
                selected_shark_guid = str(selected_shark_guid_raw)
            if (current_stage_type == "SingleShark_WordAtBottom"):
                if (len(current_active_sharks) > 0):
                    first_active_shark = current_active_sharks[0]
                    if (len(first_active_shark) > 0):
                        selected_shark_guid = str(first_active_shark[0])
            elif (current_stage_type == "OceanFloor_ShipwreckBonus"):
                selected_shark_guid = None
            
            #Now determine the "expected keypress" at this timepoint
            if (selected_shark_guid is not None):
                try:
                    cur_shark_word_idx = sharks[selected_shark_guid]["cur_word_idx"]
                    cur_shark_letter_idx = sharks[selected_shark_guid]["cur_letter_idx"]
                    this_shark_words = sharks[selected_shark_guid]["shark_data"][2]
                    this_word = this_shark_words[cur_shark_word_idx]
                    expected_keypress = this_word[cur_shark_letter_idx]
                except:
                    expected_keypress = None
                all_expected_keypresses.append(expected_keypress)
            else:
                all_expected_keypresses.append(None)

            #Now let's iterate through all alive sharks and update the cur word/letter idx
            for cur_shark_guid in alive_shark_guids:
                sharks[cur_shark_guid]["cur_word_idx"] = sharks[cur_shark_guid]["updated_word_idx"]
                sharks[cur_shark_guid]["cur_letter_idx"] = sharks[cur_shark_guid]["updated_letter_idx"]
                this_shark_num_words = int(sharks[cur_shark_guid]["shark_data"][1])
                if (sharks[cur_shark_guid]["cur_word_idx"] >= this_shark_num_words):
                    sharks[cur_shark_guid]["shark_killed"] = True

        return (all_expected_keypresses, sharks)

    #This function simply calculates the total number of keypresses that occurred and what they were.
    #It returns to things: (1) an integer representing the total number of keypresses, and (2) a list
    #of all keypresses.
    def CalculateTotalKeypresses (self):
        total_keypresses = 0
        keypresses_array = self.key_released_strings
        all_keypresses = []
        for i in range(0, len(keypresses_array)):
            total_keypresses += len(keypresses_array[i])
            if (len(keypresses_array[i]) > 0):
                all_keypresses.extend(keypresses_array[i])
        return (total_keypresses, all_keypresses)

    #This function takes the key1_string column of the typershark table and converts it to an array
    #where there are 1's in place of keypresses and 0's where no keypresses occurred.
    def ConvertKeypressSignalToBinary (self):
        keypresses_array = self.key_released_strings
        binary_keypresses = []
        for x in keypresses_array:
            if (len(x) > 0):
                binary_keypresses.append(1)
            else:
                binary_keypresses.append(0)
        return binary_keypresses

    #The purpose of this method is to calculate keypress accuracy metrics during a TyperShark
    #session. The input to this method is a Pandas dataframe representing the SQL data table
    #of a TyperShark session. It should be the "continuous" table, and not the "periodic"
    #table.
    #
    #Input parameters: "continuous" TyperShark dataframe from database
    #Outputs:
    #
    def CalculateTyperSharkMetrics (self):
        (all_expected_keypresses, sharks) = self.CalculateExpectedKeypresses()

        #Calculate the percentage of accurate keypresses
        #In this metric, we exclude anything that happened during an "OceanFloor_ShipwreckBonus" stage,
        #because the data file does not contain the appropriate data to be able to calculate accuracy during
        #that stage.
        total_keypresses = 0
        total_correct_keypresses = 0
        for idx in range(0, len(self.signal_time)):
            cur_stage = self.stage_type[idx]

            #If this is NOT the "shipwreck bonus" stage
            if (cur_stage != "OceanFloor_ShipwreckBonus"):
                #Get the current keypress
                cur_keypress = self.key_released_strings[idx]
                if (len(cur_keypress) > 0):
                    cur_keypress = cur_keypress[0]
                else:
                    cur_keypress = None

                #Check to see if the current keypress matches the expected keypress
                if (cur_keypress is not None):
                    expected_keypress = all_expected_keypresses[idx]
                    total_keypresses += 1
                    if (cur_keypress == expected_keypress):
                        total_correct_keypresses += 1
        
        #Now calculate the keypress accuracy
        try:
            percent_accurate_keypresses = 100 * (total_correct_keypresses / total_keypresses)
        except:
            percent_accurate_keypresses = float("NaN")

        #Now calculate the percentage of sharks that were killed
        total_sharks = len(sharks.keys())
        sharks_killed = 0
        for s in sharks.keys():
            cur_shark = sharks[s]
            if (cur_shark["shark_killed"]):
                sharks_killed += 1
        
        try:
            percent_sharks_killed = 100 * (sharks_killed / total_sharks)
        except:
            percent_sharks_killed = float("NaN")


        #Now calculate the total words completed and percent of words completed
        total_words = 0
        total_words_completed = 0
        for s in sharks.keys():
            cur_shark_total_words = sharks[s]["shark_data"][1]
            cur_shark_words_completed = sharks[s]["cur_word_idx"]
            total_words += cur_shark_total_words
            total_words_completed += cur_shark_words_completed
        
        try:
            percent_words_completed = 100 * (total_words_completed / total_words)
        except:
            percent_words_completed = float("NaN")

        #Now let's calculate the "words per minute" and "keys per minute"
        try:
            first_oceanfloor_idx = next(x[0] for x in enumerate(self.stage_type) if x == "OceanFloor_ShipwreckBonus")
            total_session_time = self.signal_time[first_oceanfloor_idx]
        except:
            try:
                total_session_time = self.signal_time[-1]
            except:
                total_session_time = float("NaN")

        try:
            if (math.isnan(total_session_time)):
                total_session_time = np.nanmax(np.array(self.signal_time))
        except:
            total_session_time = 0

        try:
            words_per_minute = (60 * total_words_completed) / total_session_time
            keys_per_minute = (60 * total_keypresses) / total_session_time
            correct_keys_per_minute = (60 * total_correct_keypresses) / total_session_time
            mistakes_per_minute = (60 * (total_keypresses - total_correct_keypresses)) / total_session_time
        except:
            words_per_minute = float("NaN")
            keys_per_minute = float("NaN")
            correct_keys_per_minute = float("NaN")
            mistakes_per_minute = float("NaN")

        return (sharks_killed, 
            percent_sharks_killed, 
            total_words_completed,
            percent_words_completed,
            total_keypresses, 
            percent_accurate_keypresses,
            words_per_minute,
            keys_per_minute, 
            correct_keys_per_minute, 
            mistakes_per_minute,
            total_session_time)
    