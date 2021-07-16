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

class RePlayGameDataFruitArchery(RePlayGameData):

    def __init__(self):
        super().__init__()

        #Instantiate a string to hold the exercise name, and make the default value "Grip"
        self.exercise_name = "Grip"

        #Instantiate a variable to hold the gain, and make its value 1.0 by default
        self.gain = 1.0

    def DetermineSignal (self, replay_version_code, game_name, exercise_name, gain, sensitivity):
        #The following pseudocode illustrates how RePlay transforms the signal data before saving it
        #in the data file:
        '''
        actual_force = FruitArchery_GameSettings.PuckDongle.PuckPack0.Loadcell - baseline_puck_force;
        transformed_force = actual_force;

        //Now let's apply the gain to the force (if "grip" is the chosen exercise)
        if (FruitArchery_GameSettings.StimulationExercise == ExerciseType.FitMi_Grip)
        {
            transformed_force *= FruitArchery_GameSettings.ExerciseGain;
        }

        //Now let's grab the rotation angle of the bow
        float bow_rotation_radians = 0;
        var player_bow = world.GetBow;
        if (player_bow != null)
        {
            bow_rotation_radians = player_bow.RotationRadians;
        }

        //Choose whether to pass the force or the rotation into the VNS algorithm
        //The default is to use force, which is used if grip is the exercise
        double vns_algorithm_sample = transformed_force;
        if (FruitArchery_GameSettings.StimulationExercise == ExerciseType.FitMi_Supination)
        {
            //Otherwise, if supination is the exercise, we use the bow rotation
            vns_algorithm_sample = bow_rotation_radians;
        }

        //Now pass the new sample into the vns algorithm
        bool trigger = VNS.Determine_VNS_Triggering(DateTime.Now, vns_algorithm_sample);
        '''

        #Save the exercise name and the gain so they can be referred to easily in other parts of this class
        self.exercise_name = exercise_name
        self.gain = gain

        #Create some default values
        self.signal_actual_units = "Unknown"
        self.signal_actual = []

        #RePlay version code 30 is the first version that was used in the Baylor SCI trial.
        if (replay_version_code >= 30) and hasattr(self, "signal"):
            #In Fruit Archery
            
            if (exercise_name == "Grip"):
                self.signal_actual = self.signal_force
                self.signal_actual_units = "Loadcell units (~20 grams/value)"
            elif (exercise_name == "Supination"):
                self.signal_actual = self.signal
                self.signal_actual_units = "Degrees"

        #Set a flag indicating that this object has changed
        self._p_changed = True        

    def GetGameSignal (self, use_real_world_units = True):
        result_signal = []
        result_units = "Unknown"
        if hasattr(self, "signal_actual"):
            if (use_real_world_units):
                result_signal = self.signal_actual
                result_units = self.signal_actual_units
            else:
                if (self.exercise_name == "Grip"):
                    result_signal = Enumerable(self.signal_actual).select(lambda x: x * self.gain).to_list()
                    result_units = "Transformed game units"
                elif (self.exercise_name == "Supination"):
                    #Grab the "bow rotation radians"
                    result_signal = Enumerable(self.bow_info).select(lambda x: x[3]).to_list()
                    result_units = "Transformed game units"
                else:
                    pass
                
        return (result_signal, self.signal_time, result_units)  

    def ReadGameData(self, file_path, file_name, data_start_location):
        self.filepath = file_path
        self.filename = file_name
        self.__data_start_location = data_start_location

        #Create metadata variables
        self.start_time = []
        self.game_file_version = []
        self.stage = []
        self.fire_threshold = []

        #Create varibles for saving the game information
        self.signal_time = []
        self.signal_timenum = []
        self.signal_timeelapsed = []

        self.signal = []
        self.signal_force = []

        self.arrow_exists = []
        self.arrow_flying = []
        self.arrow_info = []
        
        self.bow_exists = []
        self.bow_info = []

        self.signal = []

        self.fruit_exists = []
        self.fruit_info = []
        self.score = []

        #Create lists for rebaselining information
        self.rebaseline_time = []
        self.number_rebaseline_values = []
        self.rebaseline_values = []

        #Grab the file size in bytes
        flength = os.stat(self.filename).st_size

        with open(self.filename, 'rb') as f:
            f.seek(self.__data_start_location)
            try:
                while (f.tell() < flength - 4):
                    packet_type = RePlayDataFileStatic.read_byte_array(f, 'int')

                    #Packet 1 indicates metadata for a session
                    if packet_type == 1:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.start_time.append(convert_datenum(timenum_read))
                        self.game_file_version.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                        self.stage.append(RePlayDataFileStatic.read_byte_array(f, 'int'))

                        if self.game_file_version[0] >= 2:
                            self.fire_threshold.append(RePlayDataFileStatic.read_byte_array(f, 'int'))

                    #Packet 2 indicates frame data
                    elif packet_type == 2:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.signal_timenum.append(convert_datenum(timenum_read))
                        self.signal_timeelapsed.append(self.signal_timenum[-1]-self.signal_timenum[0])
                        self.signal_time.append(self.signal_timeelapsed[-1].total_seconds())

                        arrow_exists = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                        self.arrow_exists.append(arrow_exists)
                        if arrow_exists == 1:
                            arrow_flying  = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                            self.arrow_flying.append(arrow_flying)

                            #arrow_info [timestamp, arrow_pos_x, arrow_pos_y, arrow_vel_x, arrow_vel_y]
                            arrow_info = []
                            if arrow_flying == 1:
                                arrow_info.append(self.signal_timeelapsed[-1])
                                arrow_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                arrow_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                arrow_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                arrow_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))

                                self.arrow_info.append(arrow_info)

                            else:
                                arrow_info=[]
                                arrow_info.append(None)
                                arrow_info.append(None)
                                arrow_info.append(None)
                                arrow_info.append(None)
                                self.arrow_info.append(arrow_info)

                        else:
                            self.arrow_flying.append(None)
                            arrow_info=[]
                            arrow_info.append(None)
                            arrow_info.append(None)
                            arrow_info.append(None)
                            arrow_info.append(None)
                            arrow_info.append(None)
                            self.arrow_info.append(arrow_info)

                        bow_exists = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                        self.bow_exists.append(bow_exists)

                        bow_info = []
                        if bow_exists == 1:
                            bow_info.append(self.signal_timeelapsed[-1])

                            #File Version 2: bow_info = [bow_pos_x, bow_pos_y, bow_rot(radians)]
                            if self.game_file_version[0] >= 2:
                                #Signal force only saved after version 1

                                if self.game_file_version[0] == 2:
                                    #File version 2 saves the force as an int
                                    self.signal_force.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                                else:
                                    #File version 3 and above saves the force as a double
                                    self.signal_force.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                                self.signal.append(RePlayDataFileStatic.read_byte_array(f, 'double'))

                                bow_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                bow_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                bow_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                self.bow_info.append(bow_info)

                            #File Version 1: bow_info consists of [bow_pos_x, bow_pos_y, bow_rot(radians)]
                            elif self.game_file_version[0] == 1:
                                bow_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                bow_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                bow_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                
                                self.bow_info.append(bow_info)

                                #Convert the signal to degrees and save it out to the signal matrix
                                self.signal.append(np.degrees(bow_info[3]))

                        else:
                            if self.game_file_version[0] >= 2:
                                self.signal_force.append(None)
                                self.signal.append(None)
                                
                                bow_info.append(None)
                                bow_info.append(None)
                                bow_info.append(None)
                                self.bow_info.append(bow_info)

                            elif self.game_file_version[0] == 1:
                                bow_info.append(None)
                                bow_info.append(None)
                                bow_info.append(None)
                                self.bow_info.append(bow_info)
                                self.signal.append(None)

                        fruit_exists = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                        self.fruit_exists.append(fruit_exists)
                        
                        #fruit_info = [timestamp, fruit_pos_x, fruit_pos_y, fruit_rotation, fruit_size_x, fruit_size_y, fruit_hit]
                        fruit_info = []
                        if fruit_exists == 1:
                            fruit_info.append(self.signal_timeelapsed[-1])
                            fruit_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            fruit_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            fruit_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            fruit_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            fruit_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            fruit_info.append(RePlayDataFileStatic.read_byte_array(f, 'uint8'))

                            self.fruit_info.append(fruit_info)

                        else:
                            fruit_info.append(None)
                            fruit_info.append(None)
                            fruit_info.append(None)
                            fruit_info.append(None)
                            fruit_info.append(None)
                            fruit_info.append(None)
                            fruit_info.append(None)
                            self.fruit_info.append(fruit_info)

                        # Read in the score
                        self.score.append(RePlayDataFileStatic.read_byte_array(f, 'int32'))

                    #Packet 3 indicates event data
                    elif packet_type == 3:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.rebaseline_time.append(convert_datenum(timenum_read))

                        number_rebaseline_values = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.number_rebaseline_values.append(number_rebaseline_values)

                        temp_baselines = []
                        for _ in itertools.repeat(None, number_rebaseline_values):
                            temp_baselines.append(RePlayDataFileStatic.read_byte_array(f, 'double'))

                        self.rebaseline_values.append(temp_baselines)

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

    def CalculateFruitHitPerMinute (self):
        fruit_hit_per_minute = 0
        try:
            score_array = self.score
            total_fruit_hit = max(score_array)
            session_duration_seconds = self.signal_time[-1]
            fruit_hit_per_minute = 60 * (total_fruit_hit / session_duration_seconds)
        except:
            fruit_hit_per_minute = 0

        return fruit_hit_per_minute