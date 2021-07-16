import persistent

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

from .RePlayUtilities import convert_datenum
from .RePlayControllerData import RePlayControllerData
from .RePlayGameData import RePlayGameData
from .RePlayGameDataBreakout import RePlayGameDataBreakout
from .RePlayGameDataFruitArchery import RePlayGameDataFruitArchery
from .RePlayGameDataFruitNinja import RePlayGameDataFruitNinja
from .RePlayGameDataRepetitionsMode import RePlayGameDataRepetitionsMode
from .RePlayGameDataSpaceRunner import RePlayGameDataSpaceRunner
from .RePlayGameDataTrafficRacer import RePlayGameDataTrafficRacer
from .RePlayGameDataTyperShark import RePlayGameDataTyperShark
from .RePlayDataFileStatic import RePlayDataFileStatic
from .RePlayVNSParameters import RePlayVNSParameters
from .RePlayVNSParameters import SmoothingOptions
from .RePlayVNSParameters import Stage1_Operations
from .RePlayVNSParameters import Stage2_Operations
from .RePlayVNSParameters import BufferExpirationPolicy

class RePlayDataFile(persistent.Persistent):
        
    def __init__(self, filepath):
        self.subject_id = None
        self.md5_checksum = None
        self.version = None
        self.replay_build_date = None
        self.replay_version_name = None
        self.replay_version_code = None
        self.tablet_id = None
        self.game_id = None
        self.exercise_id = None
        self.device_type = None
        self.data_type = None
        self.session_start = None
        self.standard_range = None
        self.actual_range = None
        self.gain = None
        self.crash_detected = None
        self.aborted_file = False
        self.bad_packet_count = 0

        self.filepath = Path(filepath)
        self.filename = str(filepath)

        self.controller_data = None
        self.game_data = None

        self.__md5_checksum()
        self.__read_meta_data()

    # This method calculates the md5 checksum of the file's contents
    # This can be used for file verification
    def __md5_checksum(self):
        hash_md5 = hashlib.md5()
        with open(self.filename, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        self.md5_checksum = hash_md5.hexdigest()
        self._p_changed = True        

    def __read_meta_data(self):
        # print(f'Reading metadata from file: {self.filepath.stem}')
        # open the file and parse through to grab the meta data
        with open(self.filename, 'rb') as f:
            # seek to beginning of file and read the first 4 bytes: version number
            f.seek(0)
            self.version = RePlayDataFileStatic.read_byte_array(f, 'int32')

            if self.version < 7:
                # Read in the subject id
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.subject_id = f.read(temp_length).decode()

                # read in the game id
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.game_id = f.read(temp_length).decode()

                # read in exercise id
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.exercise_id = f.read(temp_length).decode()

                # read in device type
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.device_type = f.read(temp_length).decode()

                # read in data type. 0: Controller data; 1: Game Data
                self.data_type = RePlayDataFileStatic.read_byte_array(f, 'uint8')

                # read in the start time
                temp_time = RePlayDataFileStatic.read_byte_array(f, 'float64')
                self.session_start = RePlayDataFileStatic.convert_datenum_to_dateTime(temp_time)

                #If this is file version 6, then let's read in a few more pieces of metadata
                if (self.version == 6):
                    # read in standard range for the current exercise
                    self.standard_range = RePlayDataFileStatic.read_byte_array(f, 'double')

                    # read in gain for the current exercise
                    self.gain = RePlayDataFileStatic.read_byte_array(f, 'double')

                    # read in actual range for the current exercise
                    self.actual_range = RePlayDataFileStatic.read_byte_array(f, 'double')

                # data location starts here
                self.__data_start_location = f.tell()

            elif self.version >= 7:

                # read in the start time
                temp = RePlayDataFileStatic.read_byte_array(f, 'float64')
                self.replay_build_date = RePlayDataFileStatic.convert_datenum_to_dateTime(temp)

                # Read in the version name
                temp_name = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.replay_version_name = f.read(temp_name).decode()

                # Read in the version code
                temp_code = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.replay_version_code = f.read(temp_code).decode()

                # Read in the tablet ID
                temp_id = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.tablet_id = f.read(temp_id).decode()

                # Read in the subject id
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.subject_id = f.read(temp_length).decode()

                # read in the game id
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.game_id = f.read(temp_length).decode()

                # read in exercise id
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.exercise_id = f.read(temp_length).decode()

                # read in device type
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.device_type = f.read(temp_length).decode()

                # read in data type. 0: Controller data; 1: Game Data
                self.data_type = RePlayDataFileStatic.read_byte_array(f, 'uint8')

                # read in the start time
                temp_time = RePlayDataFileStatic.read_byte_array(f, 'float64')
                self.session_start = RePlayDataFileStatic.convert_datenum_to_dateTime(temp_time)

                # read in standard range for the current exercise
                self.standard_range = RePlayDataFileStatic.read_byte_array(f, 'double')

                # read in gain for the current exercise
                self.gain = RePlayDataFileStatic.read_byte_array(f, 'double')

                # read in actual range for the current exercise
                self.actual_range = RePlayDataFileStatic.read_byte_array(f, 'double')

                #Read in a byte that indicates whether this session was launched from the "assignment" in RePlay
                if (self.version >= 10):
                    self.launched_from_assignment = RePlayDataFileStatic.read_byte_array(f, 'uint8')

                    #Read in VNS algorithm parameter information
                    if (self.version >= 11):
                        #Read in the VNS algorithm parameters "save version"
                        vns_algo_params_save_version = RePlayDataFileStatic.read_byte_array(f, 'int32')

                        #Read in the number of bytes saved as part of the VNS algo parameters
                        vns_algo_params_num_bytes = RePlayDataFileStatic.read_byte_array(f, 'int32')

                        #Read in the actual parameters
                        vns_algo_enabled = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                        vns_algo_min_isi_ms = RePlayDataFileStatic.read_byte_array(f, 'double')
                        vns_algo_desired_isi_ms = RePlayDataFileStatic.read_byte_array(f, 'double')
                        vns_algo_selectivity = RePlayDataFileStatic.read_byte_array(f, 'double')
                        vns_algo_compensatory_selectivity = RePlayDataFileStatic.read_byte_array(f, 'double')
                        vns_algo_lookback_window = RePlayDataFileStatic.read_byte_array(f, 'double')
                        vns_algo_smoothing_window = RePlayDataFileStatic.read_byte_array(f, 'double')
                        vns_algo_noise_floor = RePlayDataFileStatic.read_byte_array(f, 'double')
                        vns_algo_trig_pos = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                        vns_algo_trig_neg = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                        vns_algo_selectivity_controlled = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                        n = RePlayDataFileStatic.read_byte_array(f, 'int32')
                        vns_algo_s1_smoothing = f.read(n).decode()
                        n = RePlayDataFileStatic.read_byte_array(f, 'int32')
                        vns_algo_s2_smoothing = f.read(n).decode()
                        n = RePlayDataFileStatic.read_byte_array(f, 'int32')
                        vns_algo_s1_operation = f.read(n).decode()
                        n = RePlayDataFileStatic.read_byte_array(f, 'int32')
                        vns_algo_s2_operation = f.read(n).decode()

                        if vns_algo_s1_smoothing == "None":
                            vns_algo_s1_smoothing = "NoSmoothing"
                        if vns_algo_s2_smoothing == "None":
                            vns_algo_s2_smoothing = "NoSmoothing"
                        if vns_algo_s1_operation == "None":
                            vns_algo_s1_operation = "NoOperation"

                        if (vns_algo_params_save_version >= 2):
                            vns_algo_typershark_lookback_size = RePlayDataFileStatic.read_byte_array(f, 'int32')
                        else:
                            vns_algo_typershark_lookback_size = float("NaN")

                        if (vns_algo_params_save_version >= 3):
                            n = RePlayDataFileStatic.read_byte_array(f, 'int32')
                            vns_algo_lookback_expiration_policy = f.read(n).decode()
                            vns_algo_lookback_window_capacity = RePlayDataFileStatic.read_byte_array(f, 'int32')
                        else:
                            vns_algo_lookback_expiration_policy = "TimeLimit"
                            vns_algo_lookback_window_capacity = 0

                        #Create a vns algorithm parameters object and property on the class
                        self.vns_algorithm_parameters = RePlayVNSParameters()
                        self.vns_algorithm_parameters.Enabled = bool(vns_algo_enabled)
                        self.vns_algorithm_parameters.Minimum_ISI = timedelta(milliseconds=vns_algo_min_isi_ms)
                        self.vns_algorithm_parameters.Desired_ISI = timedelta(milliseconds=vns_algo_desired_isi_ms)
                        self.vns_algorithm_parameters.Selectivity = vns_algo_selectivity
                        self.vns_algorithm_parameters.CompensatorySelectivity = vns_algo_compensatory_selectivity
                        self.vns_algorithm_parameters.LookbackWindow = timedelta(milliseconds=vns_algo_lookback_window)
                        self.vns_algorithm_parameters.SmoothingWindow = timedelta(milliseconds=vns_algo_smoothing_window)
                        self.vns_algorithm_parameters.NoiseFloor = vns_algo_noise_floor
                        self.vns_algorithm_parameters.TriggerOnPositive = bool(vns_algo_trig_pos)
                        self.vns_algorithm_parameters.TriggerOnNegative = bool(vns_algo_trig_neg)
                        self.vns_algorithm_parameters.SelectivityControlledByDesiredISI = bool(vns_algo_selectivity_controlled)
                        self.vns_algorithm_parameters.Stage1_Smoothing = SmoothingOptions[vns_algo_s1_smoothing]
                        self.vns_algorithm_parameters.Stage2_Smoothing = SmoothingOptions[vns_algo_s2_smoothing]
                        self.vns_algorithm_parameters.Stage1_Operation = Stage1_Operations[vns_algo_s1_operation]
                        self.vns_algorithm_parameters.Stage2_Operation = Stage2_Operations[vns_algo_s2_operation]
                        self.vns_algorithm_parameters.TyperSharkLookbackSize = vns_algo_typershark_lookback_size
                        self.vns_algorithm_parameters.VNS_AlgorithmParameters_SaveVersion = vns_algo_params_save_version
                        self.vns_algorithm_parameters.LookbackWindowExpirationPolicy = BufferExpirationPolicy[vns_algo_lookback_expiration_policy]
                        self.vns_algorithm_parameters.LookbackWindowCapacity = vns_algo_lookback_window_capacity
                
                # data location starts here
                self.__data_start_location = f.tell()

            #Scan to end to figure out when to stop looping when reading game information
            if self.data_type == 0:
                # seek to the end of file and read the final 8 bytes
                f.seek(-8, 2)
                
                # grab the file position for end of data
                self.__data_end_location = f.tell()

                # grab the number of stimulations in the file
                self.total_stimulations = RePlayDataFileStatic.read_byte_array(f, 'int32')

                # grab the number of data samples in the file
                self.__total_frames = RePlayDataFileStatic.read_byte_array(f, 'int32')
                
            elif self.data_type == 1:
                # seek to the end of file and read the final 8 bytes
                f.seek(-4, 2)
                
                # grab the file position for end of data
                self.__data_end_location = f.tell()

                # grab the number of data samples in the file
                self.__total_frames = RePlayDataFileStatic.read_byte_array(f, 'int32')

            self.crash_detected = 0
        self._p_changed = True

    def ReadData (self, trash_controller_device_data = False):
        if self.data_type == 0:
            self.controller_data = RePlayControllerData()
            self.controller_data.ReadControllerData(self.filename, self.device_type, self.__data_start_location, trash_controller_device_data)

        elif self.data_type == 1:
            
            #Determine what kind of object we need to create based on which game was played
            if self.game_id == 'FruitArchery':
                self.game_data = RePlayGameDataFruitArchery()
            elif self.game_id == 'RepetitionsMode':
                self.game_data = RePlayGameDataRepetitionsMode()
            elif self.game_id == 'ReCheck':
                self.game_data = RePlayGameDataRepetitionsMode()
            elif self.game_id == 'TrafficRacer':
                self.game_data = RePlayGameDataTrafficRacer(self.replay_version_code)
            elif self.game_id == 'Breakout':
                self.game_data = RePlayGameDataBreakout()
            elif self.game_id == 'SpaceRunner':
                self.game_data = RePlayGameDataSpaceRunner()
            elif self.game_id == 'FruitNinja':
                self.game_data = RePlayGameDataFruitNinja()
            elif self.game_id == 'TyperShark':
                self.game_data = RePlayGameDataTyperShark(self.version)
            else:
                self.game_data = RePlayGameData()

            #Read the game data for this game session
            self.game_data.ReadGameData(self.filepath, self.filename, self.__data_start_location)
            if ((int(self.replay_version_code) >= 30) or 
                ((self.game_id == 'ReCheck') and (int(self.replay_version_code) >= 11))):
                
                self.game_data.DetermineSignal(
                    int(self.replay_version_code), 
                    self.game_id, 
                    self.exercise_id, 
                    self.gain, 
                    self.standard_range)
            else:
                self.__convert_signal_to_actual_signal()

        else:
            print("Unidentified data type detected")
        
        self._p_changed = True


    def __convert_signal_to_actual_signal(self):
        
        #This function takes the signal from the game_self and converts it in to the "actual" signal, which is
        #a real unit such as grams, degrees, etc.

        #Check the list of changes for the different versions of replay to understand why certain values need to be converted
        #For details: https://docs.google.com/document/d/1wh-MwtG-2Y4iCSw5NpmOZo-8WCiXHdiuKi9bg1N4t_o/edit?usp=sharing
        if self.version <= 6:
            #Loadcell values on pucks can be multiplied by 19.230769 to convert the analog value to Grams

            controller_sensitivity={}

            #Weak
            controller_sensitivity['RepetitionsMode'] = {'Isometric Handle': 50, 'Isometric Knob': 50, 'Isometric Wrist': 50, 'Isometric Pinch': 50,
                    'Isometric Pinch Left': 50, 'Range of Motion Handle': 50, 'Range of Motion Knob': 50, 'Range of Motion Wrist': 50, 
                    'Flipping': 50, 'Supination': 50, 'Finger Twists': 50, 'Flyout': 50, 'Wrist Flexion': 50, 'Bicep Curls': 10, 'Rolling': 10, 
                    'Shoulder Abduction': 10, 'Shoulder Extension': 10, 'Wrist Deviation': 10, 'Rotate': 10, 'Grip': 50, 'Touches': 50, 
                    'Clapping': 50, 'Finger Tap': 50, 'Key Pinch': 50, 'Reach Across': 50, 'Reach Diagonal': 50, 'Reach Out': 50, 'Thumb Opposition': 50}

            
            #Medium 
            controller_sensitivity['Breakout'] = {'Isometric Handle': 100, 'Isometric Knob': 100, 'Isometric Wrist': 100, 'Isometric Pinch': 100,
                    'Isometric Pinch Left': 100, 'Range of Motion Handle': 100, 'Range of Motion Knob': 100, 'Range of Motion Wrist': 100, 
                    'Flipping': 100, 'Supination': 100, 'Finger Twists': 100, 'Flyout': 100, 'Wrist Flexion': 100, 'Bicep Curls': 25, 'Rolling': 25, 
                    'Shoulder Abduction': 25, 'Shoulder Extension': 25, 'Wrist Deviation': 25, 'Rotate': 25, 'Grip': 100, 'Touches': 100, 
                    'Clapping': 100, 'Finger Tap': 100, 'Key Pinch': 100, 'Reach Across': 100, 'Reach Diagonal': 100, 'Reach Out': 100, 'Thumb Opposition': 100}

            
            #Weak
            controller_sensitivity['TrafficRacer'] = {'Isometric Handle': 50, 'Isometric Knob': 50, 'Isometric Wrist': 50, 'Isometric Pinch': 50,
                    'Isometric Pinch Left': 50, 'Range of Motion Handle': 50, 'Range of Motion Knob': 50, 'Range of Motion Wrist': 50, 
                    'Flipping': 50, 'Supination': 50, 'Finger Twists': 50, 'Flyout': 50, 'Wrist Flexion': 50, 'Bicep Curls': 10, 'Rolling': 10, 
                    'Shoulder Abduction': 10, 'Shoulder Extension': 10, 'Wrist Deviation': 10, 'Rotate': 10, 'Grip': 50, 'Touches': 50, 
                    'Clapping': 50, 'Finger Tap': 50, 'Key Pinch': 50, 'Reach Across': 50, 'Reach Diagonal': 50, 'Reach Out': 50, 'Thumb Opposition': 50}

                
            #Medium 
            controller_sensitivity['SpaceRunner'] = {'Isometric Handle': 100, 'Isometric Knob': 100, 'Isometric Wrist': 100, 'Isometric Pinch': 100,
                    'Isometric Pinch Left': 100, 'Range of Motion Handle': 100, 'Range of Motion Knob': 100, 'Range of Motion Wrist': 100, 
                    'Flipping': 100, 'Supination': 100, 'Finger Twists': 100, 'Flyout': 100, 'Wrist Flexion': 100, 'Bicep Curls': 25, 'Rolling': 25, 
                    'Shoulder Abduction': 25, 'Shoulder Extension': 25, 'Wrist Deviation': 25, 'Rotate': 25, 'Grip': 100, 'Touches': 100, 
                    'Clapping': 100, 'Finger Tap': 100, 'Key Pinch': 100, 'Reach Across': 100, 'Reach Diagonal': 100, 'Reach Out': 100, 'Thumb Opposition': 100}

            

            #If this is a game we can apply gain to
            if self.game_id in ['Breakout', 'SpaceRunner', 'TrafficRacer']:
                gain = controller_sensitivity[self.game_id][self.exercise_id]
                self.game_data.signal_actual = list(np.asarray(self.game_data.signal) * gain)
            elif self.game_id == 'FruitArchery':
                self.game_data.signal_actual = self.game_data.signal
            elif self.game_id == 'RepetitionsMode':
                #In Repetitions Mode, when the Exercise_SaveData file version was 6 or below, we saved out
                #raw data to the data file, NOT normalized data. No gain factor was applied to the saved data.
                #Therefore, we will not multiply the signal by any gain factor in the following code.
                self.game_data.signal_actual = self.game_data.signal
            else:
                pass
        
        #in version >= 7, the actual_range was saved so we can convert using that value instead of that table above
        else:
            if self.game_id in ['Breakout', 'SpaceRunner', 'TrafficRacer']:
                self.game_data.signal_actual = list(np.asarray(self.game_data.signal) * self.actual_range)

            elif self.game_id in ['FruitArchery', 'RepetitionsMode', 'ReCheck']:
                if (int(self.replay_version_code) >= 27):
                    self.game_data.signal_actual = self.game_data.signal_not_normalized
                elif (self.replay_build_date > datetime(2019, 11, 19)):
                    #In Repetitions Mode, all saved data files with versions 7 or above used game data file version 3 or above.
                    #On November 19th 2019, a change was made to the Repetitions Mode data files. They now save the normalized data
                    #instead of the raw data. Therefore, we need to account for this. All data files that come from a build
                    #of RePlay with a build data that is November 19th 2019 or later need to multiply by the gain factor to get
                    #the real data.                    
                    self.game_data.signal_actual = list(np.asarray(self.game_data.signal) * self.actual_range)
                else:
                    self.game_data.signal_actual = self.game_data.signal
            else:
                pass

        self._p_changed = True