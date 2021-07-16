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
import persistent

from .RePlayUtilities import convert_datenum
from .RePlayGameData import RePlayGameData
from .RePlayDataFileStatic import RePlayDataFileStatic

class RePlayGameDataFruitNinja(RePlayGameData):

    def __init__(self):
        super().__init__()

    def ReadGameData(self, file_path, file_name, data_start_location):
        self.filepath = file_path
        self.filename = file_name
        self.__data_start_location = data_start_location

        self.start_time = []
        self.game_file_version = []
        self.game_duration = []

        self.signal_time = []
        self.signal_timenum = []
        self.signal_timeelapsed = []
        self.touch_info = []
        self.remaining_time = []

        self.manager_data = []
        self.game_data = []
        self.num_touches = []
        self.num_fruit = []
        self.fruit_data = []

        self.is_cutting = []
        self.num_strokes = []
        self.stroke_data = []

        self.cut_velocity = []
            
        #Grab the file size in bytes
        flength = os.stat(self.filename).st_size
        packet_type = 0

        with open(self.filename, 'rb') as f:

            # seek to the position in the file to begin reading trial information
            f.seek(self.__data_start_location)
            try:
                #Loop until end of file (minus 4 byte, since that's the final game information)
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

                        num_touches = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.num_touches.append(num_touches)
                        
                        ind_touch_info = []
                        frame_touch_info = []
                        if num_touches > 0:
                            #For each touch, info is saved as Xpos, Ypos, ID, State
                            for _ in itertools.repeat(None, num_touches):
                                ind_touch_info = []
                                ind_touch_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                ind_touch_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                ind_touch_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                                ind_touch_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                                frame_touch_info.append(ind_touch_info)
                        else:
                            ind_touch_info.append(None)
                            ind_touch_info.append(None)
                            ind_touch_info.append(None)
                            ind_touch_info.append(None)
                            frame_touch_info.append(ind_touch_info)
                        
                        self.touch_info.append(frame_touch_info)

                        if (hasattr(self, "game_file_version")):
                            if ((isinstance(self.game_file_version, list)) and (len(self.game_file_version) > 0) and (self.game_file_version[0] >= 2)):
                                self.cut_velocity.append(RePlayDataFileStatic.read_byte_array(f, 'double'))

                        self.remaining_time.append(RePlayDataFileStatic.read_byte_array(f, 'double'))

                        manager_data = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                        self.manager_data.append(manager_data)

                        #Read in the values for the following game properties: FruitHit,
                        #Fruit Created, Bombs Hit, Max Fruit Speed, Fruit Spawn Interval, Bomb Spawn Interval
                        frame_game_data = []
                        if (manager_data):
                            frame_game_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            frame_game_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            frame_game_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            frame_game_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            frame_game_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            frame_game_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                        else:
                            frame_game_data.append(None)
                            frame_game_data.append(None)
                            frame_game_data.append(None)
                            frame_game_data.append(None)
                            frame_game_data.append(None)
                            frame_game_data.append(None)

                        self.game_data.append(frame_game_data)

                        num_fruit = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.num_fruit.append(num_fruit)
                        
                        frame_fruit_data = []
                        ind_fruit_data = []

                        #fruit_id, fruit_speed, fruit_gravity, fruit_x, fruit_abs_y, fruit_is_alive, 
                        #fruit_is_obstacle, fruit_time
                        if num_fruit > 0:
                            for _ in itertools.repeat(None, num_fruit):
                                ind_fruit_data = []
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'uint8'))
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'uint8'))
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'float'))

                                frame_fruit_data.append(ind_fruit_data)
                        else:
                            ind_fruit_data.append(None)
                            ind_fruit_data.append(None)
                            ind_fruit_data.append(None)
                            ind_fruit_data.append(None)
                            ind_fruit_data.append(None)
                            ind_fruit_data.append(None)
                            ind_fruit_data.append(None)
                            ind_fruit_data.append(None)

                            frame_fruit_data.append(ind_fruit_data)

                        self.fruit_data.append(frame_fruit_data)

                        is_cutting = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                        self.is_cutting.append(is_cutting)
                        
                        frame_stroke_data = []
                        ind_stroke_data = []

                        #stroke data: [time of stroke, xpos, ypos]
                        if (is_cutting):
                            num_strokes = RePlayDataFileStatic.read_byte_array(f, 'int')
                            self.num_strokes.append(num_strokes)
                            if num_strokes > 0:
                                for _ in itertools.repeat(None, num_strokes):
                                    ind_stroke_data = []
                                    timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                                    ind_stroke_data.append(convert_datenum(timenum_read))
                                    ind_stroke_data.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                    ind_stroke_data.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                    frame_stroke_data.append(ind_stroke_data)
                            else:
                                ind_stroke_data.append(0)
                                ind_stroke_data.append(None)
                                ind_stroke_data.append(None)
                                frame_stroke_data.append(ind_stroke_data)
                        else:
                            self.num_strokes.append(0)
                            ind_stroke_data.append(None)
                            ind_stroke_data.append(None)
                            ind_stroke_data.append(None)
                            frame_stroke_data.append(ind_stroke_data)

                        self.stroke_data.append(frame_stroke_data)

                    #end of game data
                    elif packet_type == 3:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.finish_time = convert_datenum(timenum_read)
                        self.total_fruit_created = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.total_fruit_hit = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.total_bombs_created = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.total_bombs_hit = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.total_swipes = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.final_score = RePlayDataFileStatic.read_byte_array(f, 'int')

                    else:
                        self.bad_packet_count = self.bad_packet_count + 1
                        if (self.bad_packet_count > 10):
                            self.aborted_file = True
                            print("Aborting file because bad packet count exceeded 10 bad packets.")
                            return
                                                    
            except:
                print(f'\nGame Crash detected during read of file: {self.filepath.stem}')
                print(f"File location: {f.tell()}, Most recent packet type: {packet_type}")
                self.crash_detected = 1

        self._p_changed = True
    
    def CalculateTouchTrajectories(self):
        #Create an object to hold all the resulting touch trajectories
        touch_trajectories = persistent.mapping.PersistentMapping()

        #Let's iterate over the the "touch_info" object
        for t in range(0, len(self.touch_info)):
            time_elapsed = self.signal_time[t]
            for touch in self.touch_info[t]:
                if touch is not None:
                    if len(touch) >= 4:
                        touch_x = touch[0]
                        touch_y = touch[1]
                        touch_id = touch[2]
                        if (touch_id is not None):
                            if (not (touch_id in touch_trajectories)):
                                new_touch_object = persistent.mapping.PersistentMapping()
                                new_touch_object["x"] = persistent.list.PersistentList()
                                new_touch_object["y"] = persistent.list.PersistentList()
                                new_touch_object["t"] = persistent.list.PersistentList()
                                touch_trajectories[touch_id] = new_touch_object

                            touch_trajectories[touch_id]["x"].append(touch_x)
                            touch_trajectories[touch_id]["y"].append(touch_y)
                            touch_trajectories[touch_id]["t"].append(time_elapsed)

                                
        
        return touch_trajectories

    def CalculateObjectTrajectories(self, only_fruit = False):
        #Create an object to hold all the resulting touch trajectories
        object_trajectories = persistent.mapping.PersistentMapping()

        #Let's iterate over the the "touch_info" object
        for t in range(0, len(self.fruit_data)):
            time_elapsed = self.signal_time[t]

            for object_data in self.fruit_data[t]:
                if object_data is not None:
                    if len(object_data) >= 4:
                        object_id = object_data[0]
                        object_x = object_data[3]
                        object_y = object_data[4]
                        object_is_alive = object_data[5]
                        object_is_bomb = object_data[6]

                        #If the "only fruit" flag is set, and this is a bomb, then skip it
                        if (object_is_bomb and only_fruit):
                            continue
                        
                        if (object_id is not None):
                            if (not (object_id in object_trajectories)):
                                new_object = persistent.mapping.PersistentMapping()
                                new_object["t"] = persistent.list.PersistentList()
                                new_object["x"] = persistent.list.PersistentList()
                                new_object["y"] = persistent.list.PersistentList()
                                new_object["is_alive"] = persistent.list.PersistentList()
                                new_object["is_bomb"] = persistent.list.PersistentList()
                                object_trajectories[object_id] = new_object

                            object_trajectories[object_id]["t"].append(time_elapsed)
                            object_trajectories[object_id]["x"].append(object_x)
                            object_trajectories[object_id]["y"].append(object_y)
                            object_trajectories[object_id]["is_alive"].append(object_is_alive)
                            object_trajectories[object_id]["is_bomb"].append(object_is_bomb)
        
        return object_trajectories

    def GetFruitNinjaRepetitionData (self, touch_trajectories):
        result_repetition_count = 0
        result_rep_start_idx = []
        result_time_moving = 0
        result_percent_time_moving = 0

        if ((self.signal_time is not None) and (len(self.signal_time) > 0)):
            total_session_duration = self.signal_time[-1]

            if (touch_trajectories is not None):
                result_repetition_count = len(touch_trajectories)

                for touch_key in touch_trajectories:
                    touch_object = touch_trajectories[touch_key]
                    touch_time_list = touch_object["t"]
                    touch_start_time = touch_time_list[0]
                    touch_end_time = touch_time_list[-1]
                    touch_duration = touch_end_time - touch_start_time
                    touch_start_idx = next(x[0] for x in enumerate(self.signal_time) if x[1] >= touch_start_time)
                    result_rep_start_idx.append(touch_start_idx)
                    result_time_moving += touch_duration

            if (total_session_duration != 0):
                result_percent_time_moving = (result_time_moving / total_session_duration) * 100.0
            else:
                result_percent_time_moving = 0

        return (result_repetition_count, result_rep_start_idx, timedelta(seconds = result_time_moving), result_percent_time_moving)

    def GetRepetitionData(self, exercise_id):
        touch_trajectories = self.CalculateTouchTrajectories()
        return self.GetFruitNinjaRepetitionData(touch_trajectories)

    def GetGameSignal (self, use_real_world_units = True):
        result = []
        result_time = []
        cur_touch_id = -1
        start_x = 0
        start_y = 0
        start_t = 0

        if (self.signal_time is not None) and (len(self.signal_time) > 0):
            result_time = self.signal_time

            if ((hasattr(self, "cut_velocity")) and (len(self.cut_velocity) > 0)):
                result = self.cut_velocity
            else:
                for t_idx in range(0, len(self.signal_time)):
                    cur_cut_velocity = 0
                    touch = self.touch_info[t_idx]
                    if (touch is not None) and (len(touch) > 0):
                        touch = touch[0]
                        touch_x = touch[0]
                        touch_y = touch[1]
                        touch_id = touch[2]

                        if (touch_id is not None):
                            #A new touch is beginning
                            if (touch_id != cur_touch_id):
                                cur_touch_id = touch_id
                                start_x = touch_x
                                start_y = touch_y
                                start_t = self.signal_time[t_idx]
                            else:
                                #A touch is being continued
                                cur_distance = math.hypot(touch_x - start_x, touch_y - start_y)
                                delta_time = self.signal_time[t_idx] - start_t
                                cur_cut_velocity = cur_distance / delta_time
                    
                    result.append(cur_cut_velocity)
            
        return (result, result_time, "Pixels per second")
                
    def CalculateSwipeAccuracy(self):
        touch_trajectories = self.CalculateTouchTrajectories()
        fruit_trajectories = self.CalculateObjectTrajectories(only_fruit=True)

        total_fruit_hit = 0
        try:
            #The easiest way to get the total number of fruit hit
            total_fruit_hit = self.total_fruit_hit
        except:
            #The second way to get the total number of fruit hit
            try:
                if len(self.game_data) > 0:
                    final_frame = self.game_data[-1]
                    if (len(final_frame) > 0):
                        total_fruit_hit = final_frame[0]
            except:
                total_fruit_hit = None

        #The final way to get the total number of fruit hit
        if (total_fruit_hit is None):
            total_fruit_hit = 0
            for f_key in fruit_trajectories:
                f = fruit_trajectories[f_key]
                f_is_alive = f["is_alive"]
                if not (f_is_alive[-1]):
                    total_fruit_hit += 1

        total_touches = len(touch_trajectories)
        swipe_accuracy = 0
        try:
            swipe_accuracy = 100 * (total_fruit_hit / total_touches)
        except:
            swipe_accuracy = 0

        if (swipe_accuracy > 100):
            swipe_accuracy = 100

        return swipe_accuracy

