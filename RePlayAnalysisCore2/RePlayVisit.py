import persistent

import os
import struct
import time
import itertools
from datetime import datetime
from datetime import timedelta
from dateutil import parser
from pathlib import Path

from RePlayAnalysisCore2 import RePlayUtilities


class RePlayVisit(persistent.Persistent):

    def __init__(self):
        self.start_time = datetime.min
        self.end_time = datetime.min
        self.is_at_home_visit = False
        self.assignment_name = ""
        self.activities = persistent.list.PersistentList()
        self.tags = persistent.mapping.PersistentMapping()
        self.parent_participant = None

    def GetDatesInRangeOfVisit (self, exclude_first_day = False):
        #Find all dates between start time and end time (inclusive)
        start_day = self.start_time.date()
        end_day = self.end_time.date()
        dates_in_range = [start_day + timedelta(days = x) for x in range((end_day - start_day).days + 1)]
        if (exclude_first_day):
            dates_in_range = dates_in_range[1:len(dates_in_range)]       
        return dates_in_range

    def GetActivitiesOnDate (self, desired_date):
        #Define the beginning and end of the time range for the day
        desired_start_time = datetime.combine(desired_date, datetime.min.time())
        desired_end_time = datetime.combine(desired_date, datetime.min.time())
        desired_end_time = desired_end_time.replace(hour = 23, minute = 59, second = 59)

        #Now look for activities that occurred within that time range
        indices_of_sessions_that_match_by_time = [idx for idx, x in enumerate(self.activities) \
            if RePlayUtilities.time_in_range(desired_start_time, desired_end_time, x.start_time)]   

        result = []
        for i in range(0, len(indices_of_sessions_that_match_by_time)):
            result.append(self.activities[indices_of_sessions_that_match_by_time[i]])
        
        return result



        
