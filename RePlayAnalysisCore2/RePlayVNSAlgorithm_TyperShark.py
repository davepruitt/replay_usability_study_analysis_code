import numpy as np
from datetime import datetime
from datetime import timedelta
from py_linq import Enumerable

from .RePlayVNSParameters import RePlayVNSParameters
from .RePlayVNSParameters import SmoothingOptions
from .RePlayVNSParameters import Stage1_Operations
from .RePlayVNSParameters import Stage2_Operations
from .RePlayVNSParameters import BufferExpirationPolicy

class RePlayVNSAlgorithm_TyperShark:

    @staticmethod
    def ProcessSignal (signal_ts, vns_parameters):
        #How to use this function:
        #   You must pass in 2 parameters, as follows:
        #   1. signal_ts = an array that holds the timestamps for keypress, in units of seconds
        #   2. vns_parameters = an object that holds the vns parameters used during this session, of type RePlayVNSParameters

        #Instantiate an empty array to be used as the result
        result = []

        if (isinstance(vns_parameters, RePlayVNSParameters)):
            #Calculate the interval between each keypres
            keypress_intervals = abs(np.diff(signal_ts))

            #Now take the inverse of the interval
            for i in range(0, len(keypress_intervals)):
                if keypress_intervals[i] > 0:
                    keypress_intervals[i] = 1.0 / keypress_intervals[i]

            #Assign to the result
            result = keypress_intervals

        return result
            
