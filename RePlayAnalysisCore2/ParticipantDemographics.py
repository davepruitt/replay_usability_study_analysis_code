import persistent
import pandas
from .ReadGoogleSpreadsheet import GoogleSheets

class ParticipantDemographics(persistent.Persistent):

    #Constructor
    def __init__(self):
        self.participants = pandas.DataFrame([], columns = [
            "UID",
            "HasBrainInjury",
            "Age",
            "Gender",
            "Handedness",
            "InjuryType",
            "InjuryDate",
            "MotorImpairedSide"
        ])

    def LoadParticipantDemographicsFromGoogle (self, sheet_id, tab_name):
        participants_table = GoogleSheets.ReadSpreadsheetWithID_ReturnPandasDataFrame(sheet_id, tab_name)

        self.participants = self.participants[0:0]
        for _, p in participants_table.iterrows():
            self.participants = self.participants.append({
                "UID" : p["UID"],
                "HasBrainInjury" : p["Brain Injury"],
                "Age" : p["Age"],
                "Gender" : p["Gender"],
                "Handedness" : p["Handedness"],
                "InjuryType" : p["Injury Type"],
                "InjuryDate" : p["Date of Injury"],
                "MotorImpairedSide" : p["Motor Impaired"]
            },
            ignore_index = True)
        self._p_changed = True

    def LoadParticipantDemographicsFromRedCap (self, api_key, api_url, report_id):
        self._p_changed = True
