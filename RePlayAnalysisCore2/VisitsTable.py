import persistent
import pandas

from datetime import datetime
from datetime import timedelta
from dateutil import parser

from .ReadGoogleSpreadsheet import GoogleSheets

class VisitsTable(persistent.Persistent):

    #Constructor
    def __init__(self):
        self.visits = pandas.DataFrame([], columns = [
            "UID",
            "Prescription",
            "Setting",
            "Date",
            "SetupDate",
            "StartDate",
            "EndDate",
            "StartTime",
            "EndTime"
        ])

    def LoadVisitsTableFromGoogle (self, sheet_id, tab_name):
        visits_table = GoogleSheets.ReadSpreadsheetWithID_ReturnPandasDataFrame(sheet_id, tab_name)
        self.visits = self.visits[0:0]
        for _, p in visits_table.iterrows():
            self.visits = self.visits.append({
                "UID" : p["UID"],
                "Prescription" : p["Prescription"],
                "Setting" : p["Setting"],
                "Date" : p["Date"],
                "SetupDate" : p["Setup Date"],
                "StartDate" : p["Start Date"],
                "EndDate" : p["End Date"],
                "StartTime" : p["Start Time"],
                "EndTime" : p["End Time"]
            },
            ignore_index = True)      
        self._p_changed = True

    #Define a function which calculates the start/end times of a visit
    #The "current_visit" parameter should be a single row from a pandas
    #dataframe that comes from the "visits" table of the database.
    #If the visit does not contain valid start/end times (for a clinic visit)
    #or valid start/end dates (for a take-home session) then this function
    #will raise an exception.
    @staticmethod
    def CalculateVisitBounds (current_visit):

        #Define some initial values
        start_time = None
        end_time = None
        date_time_conversion_successful = True
        is_current_visit_in_clinic = False

        #Grab the date and time of the current visit
        date_of_clinic_visit_string = current_visit["Date"]
        time_of_clinic_visit_start_string = current_visit["StartTime"]
        time_of_clinic_visit_end_string = current_visit["EndTime"]
        date_of_home_setup_string = current_visit["SetupDate"]
        date_of_home_start_string = current_visit["StartDate"]
        date_of_home_finish_string = current_visit["EndDate"]

        #Check to see if EVERY date/time in the table is blank/empty
        all_date_and_time_strings = [date_of_clinic_visit_string, \
            time_of_clinic_visit_start_string, time_of_clinic_visit_end_string, \
            date_of_home_setup_string, date_of_home_start_string, \
            date_of_home_finish_string]
        if all( ((not x) or (x is None)) for x in all_date_and_time_strings):
            #If all dates/times are empty, throw an exception and exit
            raise ValueError("This does not appear to be a valid visit")

        #Check to see if this is a clinic visit or an at-home session
        if (not date_of_clinic_visit_string) or (date_of_clinic_visit_string is None):
            #In this scenario, the date of the clinic visit is an empty string
            #Therefore, we must assume this row represents an at-home session
            try:
                start_time = parser.parse(date_of_home_setup_string)
                end_time = parser.parse(date_of_home_finish_string)
                end_time = end_time.replace(hour = 23, minute = 59, second = 59)
            except:
                #If the process failed, throw an exception
                raise ValueError("This does not appear to be a valid visit")

        else:
            #In this scenario, the date of the clinic visit is NOT an empty string
            #Therefore this must represent a visit IN the clinic
            is_current_visit_in_clinic = True

            try:
                #Let's parse the date and time of the visit into datetime objects
                date_of_clinic_visit = parser.parse(date_of_clinic_visit_string).date()
                time_of_clinic_start = parser.parse(time_of_clinic_visit_start_string).time()
                time_of_clinic_end = parser.parse(time_of_clinic_visit_end_string).time()

                #Now combine the date and time objects to create a start/end date+time for the whole visit
                start_time = datetime.combine(date_of_clinic_visit, time_of_clinic_start)
                end_time = datetime.combine(date_of_clinic_visit, time_of_clinic_end)
            except:
                #If the process failed, throw an exception
                raise ValueError("This does not appear to be a valid visit")
                
        return (start_time, end_time)            