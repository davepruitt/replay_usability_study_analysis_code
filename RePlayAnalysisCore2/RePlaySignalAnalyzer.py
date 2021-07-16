#
#   RePlaySignalAnalysis.py
#   Original author: David Pruitt
#   Date created: 31 March 2020
#   Purpose: To consolidate functions used in analyzing RePlay signals
#       into one useful file.
#

import numpy
from datetime import datetime
from datetime import timedelta
from collections import deque
from enum import Enum, unique

class RePlaySignalAnalyzer:

    #region Enumerations

    @unique
    class RepCountStyle(Enum):
        COUNT_ONLY_POSITIVE_MOVEMENTS = 1
        COUNT_ONLY_NEGATIVE_MOVEMENTS = 2
        COUNT_BOTH_POSITIVE_AND_NEGATIVE = 3

    @unique
    class RepCompletionCriteria(Enum):
        UNIDIRECTIONAL = 1,
        BIDIRECTIONAL = 2

    #endregion

    #region Constructor

    def __init__(self, exercise_type, signal, compensatory_signal = None, signal_timestamps = None):

        #Initialize some instance variables

        #Save the exercise type that was passed in.
        self.exercise_type = exercise_type
        
        #Save the signal timestamps for future use
        self.signal_timestamps = signal_timestamps
        
        #This is the sampling frequency of the incoming signal (samples/second)
        self.sampling_frequency = 60

        #Define duration of the smoothing window in units of seconds
        self.smoothing_window = 0.3

        #This calculates the number of samples to smooth across for the smoothing window
        self.smoothing_window_length = round(self.sampling_frequency * self.smoothing_window)

        #
        self.averaging_window = self.smoothing_window_length + (0.1 * self.sampling_frequency)

        #Define VNS triggering parameters
        self.vns_trigger_on_positive_movements = True
        self.vns_trigger_on_negative_movements = True
        self.vns_trigger_positive_selectivity = 0.1
        self.vns_trigger_negative_selectivity = 0.1
        self.vns_compensation_selectivity = 0.2
        self.vns_stimulation_timeout_period = timedelta(seconds = 10)
        self.vns_stimulation_lookback_period = timedelta(seconds = 30)

        #Process the signal that was passed into the class
        self.processed_signal = self.__process_signal(signal)

        #Process the compensatory signal (if it was provided)
        self.processed_compensatory_signal = None
        if compensatory_signal is not None:
            self.processed_compensatory_signal = self.__process_signal(compensatory_signal)

    #endregion

    #region Private methods

    #This method converts the signal from raw force/angle data to a 
    #signal that describes how much "movement" was occurring at any time during
    #the session/game.
    def __process_signal (self, signal):

        #
        # Explanation of the algorithm: TO DO 
        #

        #This will be the final, processed signal
        result_signal = []

        #Declare a temporary signal
        temp_signal = deque()

        #~~~~~~~~~~~~~~~~~~~Begin loooping stepping through signal~~~~~~~~~~~~~~~~~~~~~~~~~~~
        for idx, current_val in enumerate(signal):

            #Add the current signal value to the temporary buffer
            temp_signal.append(current_val)
            if (len(temp_signal) >= self.averaging_window):
                temp_signal.popleft()
            
            if (idx < self.smoothing_window_length):
                #If we haven't filled up to our long smoothing window yet, fill with 0 and skip to next iteration of for loop
                result_signal.append(0)
            else:
                #Apply a running average filter, then take the sum of the gradient within the smoothing window
                s = numpy.convolve(temp_signal, numpy.ones(5) / 5, mode = "valid")
                g = numpy.gradient(s)
                smoothing_window_vals = numpy.asarray(g[-self.smoothing_window_length:])
                result_val = sum(smoothing_window_vals)
                result_signal.append(result_val)

        return result_signal

    #This method returns a set of noisefloors which can be used by other methods in this class
    #to determine when repetitions or VNS triggers should happen. The noisefloors are different
    #depending upon the exercise being done. These noise floors were originally calculated by
    #Eric.
    def __get_noisefloor(self, exercise_type):
        
        #These noisefloors are mean + 3std, and calculated after passing to the 
        #calculate_adaptive_trigger_times function with a 300ms sliding window
        nf_dict={}

        #FitMi Replay Exercises
        nf_dict['Reach Across'] = 3
        nf_dict['Rotate'] = 3.5
        nf_dict['Rolling'] = 3.5
        nf_dict['Supination'] = 3.5
        nf_dict['Grip'] = 3
        nf_dict['Finger Tap'] = 3

        #Fitmi reps mode exercises
        nf_dict['Shoulder Abduction'] = 3.5
        nf_dict['Bicep Curls'] = 3.5
        nf_dict['Flipping'] = 3.5

        #RePlay devices
        nf_dict['Range of Motion Handle'] = 3.5
        nf_dict['Range of Motion Wrist'] = 3.5
        nf_dict['Range of Motion Knob'] = 3.5
        nf_dict['Isometric Handle'] = 3.5
        nf_dict['Isometric Wrist'] = 3.5
        nf_dict['Isometric Knob'] = 3.5
        nf_dict['Isometric Pinch'] = 3.5
        nf_dict['Isometric Pinch Left'] = 3.5
        
        #Touchscreen
        nf_dict['Touch'] = 0

        #Keyboard
        nf_dict['Typing'] = 0

        if (exercise_type in nf_dict):
            noise_floor = nf_dict[exercise_type]
        else:
            noise_floor = 3.5
        
        return (noise_floor)

    #endregion

    #region Public methods

    #This method returns the following to the caller:
    #   1. An array the same size as the original signal. The value of each element is the positive trigger
    #       threshold at that timepoint in the signal.
    #   2. An array the same size as the original signal. The value of each element is the negative trigger
    #       threshold at that timepoint in the signal.
    #   3. An array the same size as the original compensatory signal. The value of each element is the
    #       compensatory threshold at that timepoint in the signal. The compensatory threshold is the threshold
    #       at which VNS will NOT be triggered, if the compensatory signal exceeds that threshold.
    def CalculateVNSTriggerThresholds (self):

        #Define some variables which will be returned to the caller
        result_positive_threshold = []
        result_negative_threshold = []
        result_compensatory_threshold = []

        #Get the noise threshold for the current exercise
        noise_floor = self.__get_noisefloor(self.exercise_type)

        #Calculate the number of the samples that we should "look back" while calculating thresholds
        lookback_number_of_samples = int(self.vns_stimulation_lookback_period.total_seconds() * self.sampling_frequency)

        #Loop through the primary signal
        for idx, current_value in enumerate(self.processed_signal):

            #Calculate the point in the signal at which we should look back to
            lookback_idx = idx - lookback_number_of_samples
            if (lookback_idx < 0):
                lookback_idx = 0
            
            #Take a slice of the array from that point until the current point
            slice_of_signal = numpy.asarray(self.processed_signal[lookback_idx:idx], dtype = numpy.float)

            #Separate the positive and negative sides of the signal
            positive_values = slice_of_signal[slice_of_signal >= noise_floor]
            negative_values = slice_of_signal[slice_of_signal <= -noise_floor]

            #Calculate the threshold for the current slice
            positive_threshold = noise_floor
            negative_threshold = -noise_floor
            if len(positive_values) > 1:
                positive_threshold = numpy.percentile(positive_values, 
                    100 * (1 - self.vns_trigger_positive_selectivity))
            if len(negative_values) > 1:
                negative_threshold = -numpy.percentile(numpy.negative(negative_values), 
                    100 * (1 - self.vns_trigger_negative_selectivity))
            
            #Add these new thresholds to the result arrays
            result_positive_threshold.append(positive_threshold)
            result_negative_threshold.append(negative_threshold)
        
        #Now loop through the compensatory signal, if there is one
        if self.processed_compensatory_signal is not None:
            for idx, current_value in enumerate(self.processed_compensatory_signal):

                #Calculate the point in the signal at which we should look back to
                lookback_idx = idx - lookback_number_of_samples
                if (lookback_idx < 0):
                    lookback_idx = 0
                
                #Take a slice of the array from that point until the current point
                slice_of_signal = numpy.asarray(self.processed_compensatory_signal[lookback_idx:idx], dtype = numpy.float)

                #Calculate the threshold for the current slice
                comp_threshold = 0
                if len(slice_of_signal) > 1:
                    comp_threshold = numpy.percentile(slice_of_signal, 100 * (1 - self.vns_compensation_selectivity))
                
                #Add these new thresholds to the result arrays
                result_compensatory_threshold.append(comp_threshold)

        return (result_positive_threshold, result_negative_threshold, result_compensatory_threshold)

    #This method returns the following to the caller:
    #   1. The index into the original signal at which each VNS trigger occurs
    #   2. The time at which each VNS trigger occurs (in seconds, 0 is the start of the session)
    def CalculateVNSTriggerTimes (self, thresholds = None):

        #Create some variables to store the results of this function
        result_vns_trigger_idx = []
        result_vns_trigger_timestamps = []

        #Calculate the trigger thresholds, OR use the the thresholds passed in by the caller
        positive_threshold = []
        negative_threshold = []
        compensatory_threshold = []
        if not thresholds:
            (positive_threshold, negative_threshold, compensatory_threshold) = self.CalculateVNSTriggerThresholds()
        else:
            positive_threshold = thresholds[0]
            negative_threshold = thresholds[1]
            compensatory_threshold = thresholds[2]
        
        #Before continuiing, we must make sure the length of the threshold arrays equals the length
        #of the processed signal array. If not, we must abort
        if ((len(positive_threshold) == len(self.processed_signal)) and 
            (len(negative_threshold) == len(self.processed_signal)) and
            (len(self.signal_timestamps) == len(self.processed_signal))):

            last_trigger_time = None
            
            #Now iterate over the signal and determine when stimulation triggers should occur
            for idx, current_value in enumerate(self.processed_signal):

                #Check to see if either the positive or negative threshold has been exceeded
                trigger_vns = False
                if (self.vns_trigger_on_positive_movements) and (current_value >= positive_threshold[idx]):
                    trigger_vns = True
                elif (self.vns_trigger_on_negative_movements) and (current_value <= negative_threshold[idx]):
                    trigger_vns = True
                
                #Check the compensatory signal
                if (self.processed_compensatory_signal is not None) and (compensatory_threshold is not None):
                    if ((len(self.processed_compensatory_signal) == len(self.processed_signal)) and
                        (len(compensatory_threshold) == len(self.processed_signal))):

                        #If we have exceeded the compensatory threshold, don't allow VNS to trigger
                        if (self.processed_compensatory_signal[idx] >= compensatory_threshold[idx]):
                            trigger_vns = False
                
                #Now, if we are attempting to trigger VNS, let's make sure the timeout has expired
                current_time = self.signal_timestamps[idx]
                elapsed_time_since_last_trigger = 0
                if last_trigger_time is not None:
                    elapsed_time_since_last_trigger = current_time - last_trigger_time
                
                #If the timeout has indeed expired, and if we should trigger, then mark this time as a VNS trigger
                if ((not last_trigger_time) or 
                    (elapsed_time_since_last_trigger >= self.vns_stimulation_timeout_period.total_seconds())):

                    if (trigger_vns):
                        last_trigger_time = current_time
                        result_vns_trigger_idx.append(idx)
                        result_vns_trigger_timestamps.append(current_time)
            
        return (result_vns_trigger_idx, result_vns_trigger_timestamps)

    #This method returns the following to the caller:
    #   1. The index into the original signal at which each "movement" was initiated
    #   2. The index at which each movement ends.
    #   3. The time at which each "movement" was initiated (in seconds, 0 is the start of the session)
    #   4. The calculated duration of each movement (in seconds)
    def CalculateRepetitionTimes (self, 
        rep_count_style = RepCountStyle.COUNT_BOTH_POSITIVE_AND_NEGATIVE,
        rep_completion_criteria = RepCompletionCriteria.BIDIRECTIONAL):

        #Define some lists that will hold the results of this function
        result_idx = []
        result_times = []
        result_durations = []
        result_final_idx = []

        #Get the noise floor for this exercise
        noise_floor = self.__get_noisefloor(self.exercise_type)

        #Do some pre-processing on the signal, depending on how we want to count reps
        signal = numpy.asarray(self.processed_signal, dtype=numpy.float)
            
        #Now let's iterate through the list
        this_movement_start_idx = 0
        is_currently_in_movement = False
        movement_phase = 0
        is_positive_trial = False
        for idx, current_value in enumerate(signal):
            if not is_currently_in_movement:
                if current_value >= noise_floor:
                    if ((rep_count_style == RePlaySignalAnalyzer.RepCountStyle.COUNT_ONLY_POSITIVE_MOVEMENTS) or 
                        (rep_count_style == RePlaySignalAnalyzer.RepCountStyle.COUNT_BOTH_POSITIVE_AND_NEGATIVE)):
                        is_currently_in_movement = True
                        this_movement_start_idx = idx
                        movement_phase = 0
                        is_positive_trial = True
                if current_value <= -noise_floor:
                    if ((rep_count_style == RePlaySignalAnalyzer.RepCountStyle.COUNT_ONLY_NEGATIVE_MOVEMENTS) or 
                        (rep_count_style == RePlaySignalAnalyzer.RepCountStyle.COUNT_BOTH_POSITIVE_AND_NEGATIVE)):
                        is_currently_in_movement = True
                        this_movement_start_idx = idx
                        movement_phase = 0
                        is_positive_trial = False
            else:
                movement_finished = False
                if ((rep_count_style == RePlaySignalAnalyzer.RepCountStyle.COUNT_BOTH_POSITIVE_AND_NEGATIVE) and 
                    (movement_phase == 1)):
                    if is_positive_trial:
                        if current_value >= noise_floor:
                            movement_phase = 2
                    else:
                        if current_value <= -noise_floor:
                            movement_phase = 2
                else:
                    if is_positive_trial:
                        if current_value < noise_floor:
                            if ((rep_count_style == RePlaySignalAnalyzer.RepCountStyle.COUNT_ONLY_POSITIVE_MOVEMENTS) or 
                                (rep_completion_criteria == RePlaySignalAnalyzer.RepCompletionCriteria.UNIDIRECTIONAL) or
                                (movement_phase == 2)):
                                movement_finished = True
                            else:
                                movement_phase = 1
                                is_positive_trial = False
                    else:
                        if current_value > -noise_floor:
                            if ((rep_count_style == RePlaySignalAnalyzer.RepCountStyle.COUNT_ONLY_NEGATIVE_MOVEMENTS) or
                                (rep_completion_criteria == RePlaySignalAnalyzer.RepCompletionCriteria.UNIDIRECTIONAL) or
                                (movement_phase == 2)):
                                movement_finished = True
                            else:
                                movement_phase = 1
                                is_positive_trial = True
                        
                if movement_finished:
                    is_currently_in_movement = False
                    starting_timestamp = self.signal_timestamps[this_movement_start_idx]
                    current_timestamp = self.signal_timestamps[idx]

                    result_idx.append(this_movement_start_idx)
                    result_final_idx.append(idx)
                    result_times.append(starting_timestamp)
                    result_durations.append(current_timestamp - starting_timestamp)
                    
        return (result_idx, result_final_idx, result_times, result_durations)

    #This method returns two values to the caller:
    #   1. The total time spent "moving" (basically, where the signal exceeds the noise threshold)
    #   2. The percentage of total time spent "moving"
    def CalculateTimeSpentMoving (self):
        working_signal = list(map(abs, self.processed_signal))
        noise_threshold = self.__get_noisefloor(self.exercise_type)
        signal_above_threshold = [x for x in working_signal if x >= noise_threshold]

        #Handle the case where signal is of length 0
        if (len(working_signal) < 1):
            return (timedelta(seconds = 0), float("NaN"))

        #Calculate the percentage of time the participant was "moving"
        percent_time_spent_moving = (len(signal_above_threshold) / len(working_signal)) * 100
        
        #Calculate the absolute total time the participant was "moving"
        absolute_seconds_spent_moving = len(signal_above_threshold) / self.sampling_frequency
        absolute_time_spent_moving = timedelta(seconds = absolute_seconds_spent_moving)

        return (absolute_time_spent_moving, percent_time_spent_moving)

    #endregion