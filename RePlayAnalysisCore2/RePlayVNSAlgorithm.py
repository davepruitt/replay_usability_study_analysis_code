import numpy as np
from datetime import datetime
from datetime import timedelta
from py_linq import Enumerable

from .RePlayVNSParameters import RePlayVNSParameters
from .RePlayVNSParameters import SmoothingOptions
from .RePlayVNSParameters import Stage1_Operations
from .RePlayVNSParameters import Stage2_Operations
from .RePlayVNSParameters import BufferExpirationPolicy

class RePlayVNSAlgorithm:

    @staticmethod
    def __diff (a):
        return RePlayVNSAlgorithm.__diff2(a, 0, len(a), False)

    @staticmethod
    def __diff2 (a, start_index, count, same_size = True):
        b = []
        for i in range(0, len(a)):
            if ((i < start_index) or (i > (start_index + count))):
                b.append(a[i])
            elif (i <= (start_index + count)):
                if ((i + 1) < len(a)):
                    b.append(a[i+1] - a[i])
                else:
                    if same_size:
                        b_to_add = 0
                        if (len(b) > 0):
                            b_to_add = b[-1]
                        b.append(b_to_add)
        return b

    @staticmethod
    def __gradient (signal):
        result = []
        if (signal is not None) and (len(signal) > 1):
            for i in range(0, len(signal)):
                if i == 0:
                    result.append(signal[i+1] - signal[i])
                elif i == (len(signal) - 1):
                    result.append(signal[i] - signal[i - 1])
                else:
                    result.append(0.5 * (signal[i + 1] - signal[i - 1]))
        else:
            result.append(0)
        return result

    @staticmethod
    def __box_smooth (signal, smoothing_factor = 3):
        result = []
        if (signal is not None) and (len(signal) > 0):
            signal_ends = Enumerable.repeat(signal[0], smoothing_factor).to_list()
            ts = []
            ts.extend(signal_ends)
            ts.extend(signal)
            ts.extend(signal_ends)

            n = (smoothing_factor * 2) + 1
            for i in range(0, len(ts)):
                m = np.nanmean(ts[i:(i+n)])
                result.append(m)
        return result

    @staticmethod
    def ProcessSignal (signal, signal_ts, vns_parameters):
        #How to use this function:
        #   You must pass in 3 parameters, as follows:
        #   1. signal = the "transformed game signal"
        #   2. signal_ts = an array that holds the timestamps for each sample in signal, in units of seconds
        #   3. vns_parameters = an object that holds the vns parameters used during this session, of type RePlayVNSParameters

        #Instantiate an empty array to be used as the result
        result = []

        #Requirement to advance: the length of the signal array and the timestamps array must be equal
        if (len(signal) == len(signal_ts)) and isinstance(vns_parameters, RePlayVNSParameters):

            #Get the smoothing window size in units of seconds
            smoothing_window_seconds = vns_parameters.SmoothingWindow.total_seconds()

            #Create the small buffer
            small_buffer = []
            small_buffer_ts = []

            #Iterate over each element of the signal
            for i in range(0, len(signal)):
                #Grab the sample
                sample = signal[i]
                sample_ts = signal_ts[i]

                #Add the new sample to the small buffer
                small_buffer.append(sample)
                small_buffer_ts.append(sample_ts)

                #Remove old values from the small buffer
                first_idx = -1
                for j in range(0, len(small_buffer_ts)):
                    if (small_buffer_ts[j] >= (sample_ts - smoothing_window_seconds)):
                        first_idx = j
                        small_buffer = small_buffer[first_idx:]
                        small_buffer_ts = small_buffer_ts[first_idx:]
                        break
                
                #Stage 1 Smoothing
                s1_buffer = small_buffer
                if (vns_parameters.Stage1_Smoothing == SmoothingOptions.AveragingFilter):
                    s1_buffer = RePlayVNSAlgorithm.__box_smooth(s1_buffer)

                #Stage 1 Operation
                s1_result = s1_buffer
                if (vns_parameters.Stage1_Operation == Stage1_Operations.SubtractMean):
                    m = np.nanmean(s1_buffer)
                    s1_result = Enumerable(s1_buffer).select(lambda x: x - m).to_list()
                elif (vns_parameters.Stage1_Operation == Stage1_Operations.Derivative):
                    s1_result = RePlayVNSAlgorithm.__diff(s1_buffer)
                elif (vns_parameters.Stage1_Operation == Stage1_Operations.Gradient):
                    s1_result = RePlayVNSAlgorithm.__gradient(s1_buffer)
                
                #Stage 2 Smoothing
                s2_buffer = s1_result
                if (vns_parameters.Stage2_Smoothing == SmoothingOptions.AveragingFilter):
                    s2_buffer = RePlayVNSAlgorithm.__box_smooth(s2_buffer)

                #Stage 2 Operation
                s2_result = 0
                if (len(s2_buffer) > 0):
                    s2_result = s2_buffer[-1]

                if (vns_parameters.Stage2_Operation == Stage2_Operations.RMS):
                    if len(s2_buffer) > 0:
                        s2_result = np.sqrt(
                            np.nansum(Enumerable(s2_buffer).select(lambda x: pow(x, 2)).to_list()) / len(s2_buffer)
                        )
                    else:
                        s2_result = 0
                elif (vns_parameters.Stage2_Operation == Stage2_Operations.SignedRMS):
                    if len(s2_buffer) > 0:
                        s2_result = np.sqrt(
                            np.nansum(Enumerable(s2_buffer).select(lambda x: pow(x, 2)).to_list()) / len(s2_buffer)
                        )
                        s2_result = s2_result * np.sign(np.nanmean(s2_buffer))
                    else:
                        s2_result = 0
                elif (vns_parameters.Stage2_Operation == Stage2_Operations.Mean):
                    if len(s2_buffer) > 0:
                        s2_result = np.nanmean(s2_buffer)
                    else:
                        s2_result = 0
                elif (vns_parameters.Stage2_Operation == Stage2_Operations.Sum):
                    if len(s2_buffer) > 0:
                        s2_result = np.nansum(s2_buffer)
                    else:
                        s2_result = 0

                #The stage 2 result is placed into the result of this function
                result.append(s2_result)
        
        return result
            
