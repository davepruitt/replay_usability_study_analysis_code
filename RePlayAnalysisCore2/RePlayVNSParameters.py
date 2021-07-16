import persistent
import transaction

from datetime import timedelta

from enum import Enum

class SmoothingOptions(Enum):
    NoSmoothing = 0
    AveragingFilter = 1

class Stage1_Operations(Enum):
    NoOperation = 0
    SubtractMean = 1
    Derivative = 2
    Gradient = 3

class Stage2_Operations(Enum):
    RMS = 0
    SignedRMS = 1
    Mean = 2
    Sum = 3
    NoOperation = 4

class BufferExpirationPolicy(Enum):
    TimeLimit = 0
    TimeCapacity = 1
    NumericCapacity = 2

class RePlayVNSParameters(persistent.Persistent):

    def __init__(self):
        self.Enabled = False
        self.Minimum_ISI = timedelta(seconds = 0)
        self.Desired_ISI = timedelta(seconds = 0)
        self.Selectivity = float("NaN")
        self.CompensatorySelectivity = float("NaN")
        self.TyperSharkLookbackSize = float("NaN")
        self.LookbackWindow = timedelta(seconds = 0)
        self.SmoothingWindow = timedelta(seconds = 0)
        self.NoiseFloor = float("NaN")
        self.TriggerOnPositive = False
        self.TriggerOnNegative = False
        self.SelectivityControlledByDesiredISI = False
        self.Stage1_Smoothing = SmoothingOptions.NoSmoothing
        self.Stage2_Smoothing = SmoothingOptions.NoSmoothing
        self.Stage1_Operation = Stage1_Operations.NoOperation
        self.Stage2_Operation = Stage2_Operations.NoOperation
        self.VNS_AlgorithmParameters_SaveVersion = 0
        self.LookbackWindowExpirationPolicy = BufferExpirationPolicy.TimeLimit
        self.LookbackWindowCapacity = 0
        