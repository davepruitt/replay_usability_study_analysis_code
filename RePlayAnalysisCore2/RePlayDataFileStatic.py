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

from .RePlayUtilities import convert_datenum

class RePlayDataFileStatic:

    @staticmethod
    def read_16byte_guid(opened_file):
        result_guid = []
        for _ in itertools.repeat(None, 16):
            result_guid.append(RePlayDataFileStatic.read_byte_array(opened_file, 'uint8'))
        return result_guid

    @staticmethod
    def read_byte_array(opened_file, desired_type):
        type_dictionary = {'char': 'c',
                    'int': 'i',
                    'int32': 'i',
                    'int8': 'b',
                    'unsigned int': 'I',
                    'uint8': 'B',
                    'float': 'f',
                    'float64': 'd',
                    'double': 'd'}

        length_dictionary = {'char': 2,
                    'int': 4,
                    'int32': 4,
                    'int8': 1,
                    'unsigned int': 4,
                    'uint8': 1,
                    'float': 4,
                    'float64': 8,
                    'double': 8}                    
        unpacked = struct.unpack(type_dictionary[desired_type], opened_file.read(length_dictionary[desired_type]))
        return unpacked[0]

    @staticmethod
    def read_restore_message(f):
        #This code handles reading in a "ReStore Service Message" packet.

        #Read in the timestamp of this message
        restore_message_time = RePlayDataFileStatic.read_byte_array(f, 'float64')
        restore_message_time = RePlayDataFileStatic.convert_datenum_to_dateTime(restore_message_time)

        #Read in how many bytes are contained in the primary message
        N = RePlayDataFileStatic.read_byte_array(f, 'int')

        #Read in the primary message itself
        restore_primary_message = f.read(N).decode()

        #Read in the number of key-value pairs that exist in the message
        N_kvp = RePlayDataFileStatic.read_byte_array(f, 'int')

        #Now read in each key-value pair
        restore_secondary_message = {}
        for i in range(0, N_kvp):
            #Read in the length of the key
            N_key = RePlayDataFileStatic.read_byte_array(f, 'int')

            #Read in the key
            restore_kvp_key = f.read(N_key).decode()

            #Read in the length of the value
            N_value = RePlayDataFileStatic.read_byte_array(f, 'int')

            #Read in the value
            restore_kvp_value = f.read(N_value).decode()

            restore_secondary_message[restore_kvp_key] = restore_kvp_value

        result = {}
        result["time"] = restore_message_time
        result["primary"] = restore_primary_message
        result["secondary"] = restore_secondary_message
        return result

    @staticmethod
    def convert_datenum_to_dateTime(datenum):
        """
        Convert Matlab datenum into Python datetime.
        :param datenum: Date in datenum format
        :return:        Datetime object corresponding to datenum.
        """
        days = datenum % 1
        return datetime.fromordinal(int(datenum)) \
               + timedelta(days=days) \
               - timedelta(days=366)

    @staticmethod
    def calculate_timedelta_from_datenums(initial_datenum, final_datenum):
        initial_datetime = RePlayDataFileStatic.convert_datenum_to_dateTime(initial_datenum)
        final_datetime = RePlayDataFileStatic.convert_datenum_to_dateTime(final_datenum)
        delta = (final_datetime - initial_datetime).total_seconds()
        return delta

