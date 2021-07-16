import persistent

import os
import struct
import time
import itertools
import hashlib
import numpy as np
import pandas
import json

import os.path
from os import path

from pathlib import Path

from datetime import datetime
from datetime import timedelta
from pathlib import Path

from .RePlayUtilities import convert_datenum

class ReTrieveDataFile(persistent.Persistent):

    def __init__(self, filepath):
        self.exercise_name = "ReTrieve"
        self.md5_checksum = None
        self.filename = filepath
        self.json_data = None
        self.__md5_checksum()

    def __md5_checksum(self):
        hash_md5 = hashlib.md5()
        with open(self.filename, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        self.md5_checksum = hash_md5.hexdigest()
        self._p_changed = True             

    def read_data(self):
        #Check to see if the configuration file exists. If it does, read it in
        if (path.exists(self.filename)):
            with open(self.filename) as json_file:
                self.json_data = json.load(json_file)
                self._p_changed = True