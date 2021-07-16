import persistent
import pandas

from datetime import datetime
from datetime import timedelta
from dateutil import parser

from .ReadGoogleSpreadsheet import GoogleSheets

class LoadedFilesTable(persistent.Persistent):

    #Constructor
    def __init__(self):
        self.loaded_files = pandas.DataFrame([], columns = [
            "UID",
            "file_name",
            "md5_checksum"
        ])

    def IsFileAlreadyLoaded (self, filename, md5checksum):
        already_loaded = False
        pre_existing_loaded_file = self.loaded_files[
            (self.loaded_files["file_name"] == filename) & (self.loaded_files["md5_checksum"] == md5checksum)]
        if (len(pre_existing_loaded_file) > 0):
            already_loaded = True
        else:
            already_loaded = False
        return already_loaded

    def AppendLoadedFileToTable (self, participant_id, filename, md5checksum):
        #Add this file to the list of loaded files
        self.loaded_files = self.loaded_files.append({
            "UID" : participant_id,
            "file_name" : filename,
            "md5_checksum" : md5checksum
        }, ignore_index = True)   

        self._p_changed = True     


