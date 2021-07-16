from datetime import datetime
from datetime import timedelta
from dateutil import parser
from enum import Enum, unique

from collections import deque

import json
import numpy
import os
import sys
import pandas
import matplotlib
import matplotlib.pyplot as plot
from mpl_toolkits.axes_grid1 import Divider, Size

#
# Below are general functions and classes used by RePlay analysis code
#

# The following code defines the "getch" function which reads a single character from 
# the user on the keyboard
try:
    from msvcrt import getch
except ImportError:
    def getch():
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

# This is the external-facing version of "getch"
def get_character():
    return getch()

# Function to determine the most recent file in a folder with a given naming prefix
def get_latest_file_with_prefix (folder_name, file_prefix, return_full_path_flag = False):
    file_list = os.listdir(folder_name)
    filtered_file_list = []
    for f in file_list:
        if f.startswith(file_prefix):
            filtered_file_list.append(f)
    file_list_full_path = [os.path.join(folder_name, x) for x in filtered_file_list]
    file_modified_times = [os.path.getmtime(x) for x in file_list_full_path]
    index_of_most_recent = file_modified_times.index(max(file_modified_times))
    if return_full_path_flag:
        return file_list_full_path[index_of_most_recent]
    else:
        return filtered_file_list[index_of_most_recent]


# Pkl file import methods
def importDataFromPkl(pathToPickle, pklFileName):
    """
    Get dataframe of information from the pkl file
    """
    picklePath = os.path.join(pathToPickle, pklFileName)
    try:
        data = pandas.read_pickle(picklePath)
    except (FileNotFoundError, IOError):
        print("ERROR: Path to pickle file not found! Check path, pickle file name, and that pickle files have been properly generated.")
        print("Unrecognized path: " + picklePath)
        print("Skipping file...")
    except: 
        print("Unexpected error:", sys.exc_info()[0])
        raise
    return data

# Convert a python object to JSON string
def ObjectToJSONString(row):
    """
    Convert a list object to a JSON string to upload to database
    """
    return json.dumps(row).encode('utf8')

# Convert a JSON string to python object
def JSONstringToObject(row):
    """
    Convert a JSON string from the database to a list object
    """
    return json.loads(row.decode('utf8'))

# This function converts a Matlab datenum into a Python datetime
def convert_datenum(datenum):
    """
    Convert Matlab datenum into Python datetime.
    :param datenum: Date in datenum format
    :return:        Datetime object corresponding to datenum.
    """
    days = datenum % 1
    return datetime.fromordinal(int(datenum)) \
            + timedelta(days=days) \
            - timedelta(days=366)

# This function converts a Python datetime to a Matlab datenum format
def convert_python_datetime_to_matlab_datenum (dt):
   mdn = dt + timedelta(days = 366)
   frac_seconds = (dt-datetime.datetime(dt.year,dt.month,dt.day,0,0,0)).seconds / (24.0 * 60.0 * 60.0)
   frac_microseconds = dt.microsecond / (24.0 * 60.0 * 60.0 * 1000000.0)
   return mdn.toordinal() + frac_seconds + frac_microseconds

# This function checks to see if a datetime "x" falls within two other
# datetimes "start" and "end"
def time_in_range(start, end, x):
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end

# This function returns a list of possible exercises that can be done, given an "exercise type"
# as an input parameter. The exercise type can be "FitMi" or "RePlay"
def get_exercise_list(exercise_type):

    if exercise_type == 'FitMi':
        arm_exercises = ['Touches', 'Reach Across', 'Clapping', 'Reach Out', 
                'Reach Diagonal', 'Supination', 'Bicep Curls', 'Shoulder Extension', 
                'Shoulder Abduction', 'Flyout']
        hand_exercises = ['Wrist Flexion', 'Wrist Deviation', 'Grip', 'Rotate', 'Key Pinch',
                'Finger Tap', 'Thumb Press', 'Finger Twists', 'Rolling', 'Flipping']
        fitmi_exercises = arm_exercises + hand_exercises
        return(fitmi_exercises)

    elif exercise_type == 'RePlay':
        replay_exercises = ['Isometric Handle', 'Isometric Knob', 'Isometric Wrist', 'Isometric Pinch',
            'Isometric Pinch Left', 'Range of Motion Handle', 'Range of Motion Knob', 'Range of Motion Wrist']
        return(replay_exercises)

# This function returns a list of "games" or "activities" that we may encounter when analyzing RePlay data.
def get_activities_list():
    replay_activities = ['Breakout', 'FruitArchery', 'FruitNinja', 'RepetitionsMode',
            'SpaceRunner', 'TrafficRacer', 'TyperShark']
    return(replay_activities)

# This class will be used to work with noise floors
class NoiseFloor:
    NoiseFloorDictionary = { \
        "Reach Across" : 3, \
        "Rotate" : 3.5, \
        "Rolling" : 3.5, \
        "Supination" : 3.5, \
        "Grip" : 3.5, \
        "Finger Tap" : 3, \
        "Shoulder Abduction" : 3.5, \
        "Bicep Curls" : 3.5, \
        "Flipping" : 3.5, \
        "Range of Motion Wrist" : 3.5, \
        "Isometric Handle" : 3.5, \
        "Isometric Wrist" : 3.5, \
        "Touch" : 0, \
        "Typing" : 0 \
        }

#Define a function which calculates the start/end times of a visit
#The "current_visit" parameter should be a single row from a pandas
#dataframe that comes from the "visits" table of the database.
#If the visit does not contain valid start/end times (for a clinic visit)
#or valid start/end dates (for a take-home session) then this function
#will raise an exception.
def calculate_visit_bounds (current_visit):

    #Define some initial values
    start_time = None
    end_time = None
    date_time_conversion_successful = True
    is_current_visit_in_clinic = False

    #Grab the date and time of the current visit
    date_of_clinic_visit_string = current_visit["Clinic Date"]
    time_of_clinic_visit_start_string = current_visit["Start Time"]
    time_of_clinic_visit_end_string = current_visit["End Time"]
    date_of_home_setup_string = current_visit["Setup Date"]
    date_of_home_start_string = current_visit["Start Date"]
    date_of_home_finish_string = current_visit["End Date"]

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

# This function converts a "Y" to True and a "N" to False
def ConvertYesNo (text):
    return (text == "Y")
    
# This function maps a numeric value from one range onto another range. It can optionally clamp
# that value as well.
def MapRange (val, oldrange_min, oldrange_max, newrange_min, newrange_max, clamp = False):
    if clamp:
        val = np.clip(val, oldrange_min, oldrange_max)
    return (val - oldrange_min) / (oldrange_max - oldrange_min) * (newrange_max - newrange_min) + newrange_min


# this function returns the smoothed signal when passed a column of signal_actual data
def smooth_signal(signal):

    sampling_freq = 60

    #This calculates the number of samples to smooth across for the smoothing window
    # smoothing_window_length = round(sampling_freq*smoothing_window)
    smoothing_window_length = round(60*0.3)

    #set smoothing window to rms window + 100 (~6 samples),
    #this is to prevent edge effect on the oldest samples while running the convolution
    averaging_window = smoothing_window_length + 0.1*sampling_freq

    #this is our final, smoothed signal
    movement_signal = []

    tempsig = deque()

    loop_size = len(signal)

    #~~~~~~~~~~~~~~~~~~~Begin loooping stepping through signal~~~~~~~~~~~~~~~~~~~~~~~~~~~
    for idx in range(0, loop_size):
        tempsig.append(signal.loc[idx,'signal_actual'])

        #If we have reached our smoothing window length (300ms), remove the oldest samples from the fifo buffer
        if len(tempsig) == averaging_window:
            tempsig.popleft()

        #if we haven't filled up to our long smoothing window yet, fill with 0 and skip to next iteration of for loop
        if idx < smoothing_window_length:
            movement_signal.append(0)
            continue

        #apply a running average filter, then take the sum of the gradient within the smoothing window
        sig = numpy.convolve(tempsig, numpy.ones((5,))/5, mode='valid')
        siggrad = numpy.gradient(sig)
        smoothing_window_vals = numpy.asarray(siggrad[-smoothing_window_length:])
        signal_val = sum(smoothing_window_vals)
        movement_signal.append(signal_val)

    return movement_signal

def get_noisefloor(exerciseType):
    
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
    nf_dict['Range of Motion Wrist'] = 3.5
    nf_dict['Isometric Handle'] = 3.5
    nf_dict['Isometric Wrist'] = 3.5
    
    nf_dict['Touch'] = 0
    nf_dict['Typing'] = 0

    noise_floor = nf_dict[exerciseType]
    
    return (noise_floor)


def calculateReps_FromSignalActual(dbtable, game_id, exerciseType):
    #Modify this so that it calculates the derivative for the movement games
    if game_id in ['SpaceRunner', 'TrafficRacer', 'Breakout', 'FruitArchery']:
        
        noise_floor = get_noisefloor(exerciseType)

        #fucntion from above
        signal = smooth_signal(dbtable)

        #Convert over to numpy array
        signal = numpy.asarray(signal, dtype=numpy.float)

        signal[signal < noise_floor] = 0
        signal[signal >= noise_floor] = 1

        movement_indicies = list(signal)

        total_samples = len(signal)
        movement_samples = len(signal[signal > 0])
        percentage_time_moving = movement_samples/total_samples

        #get the signal_time column out of database table
        session_time = dbtable['signal_time'].iloc[-1]

        time_moving = percentage_time_moving * session_time

        #Calculate the number of repetitions
        min_movement_size=15
        movements = []
        ind_movement = []
        in_movement = 0

        #Index through enumerate 
        for idx, val in enumerate(movement_indicies):
            if val == 1:
                in_movement = 1
                ind_movement.append(idx)

            if val == 0:
                #If this is the first 0 after being in a movement, 
                if in_movement == 1:
                    if len(ind_movement) >= min_movement_size:
                        movements.append(ind_movement)
                    ind_movement = []
                in_movement = 0

        num_reps = len(movements)

        #convert number of samples to time measurement (sampling freq = 60)
        temp_movement_duration = [len(x)*(1/60) for x in movements]
        median_movement_duration = numpy.median(numpy.asarray(temp_movement_duration))

        return num_reps, median_movement_duration, time_moving
        
    else:
        print("\n{} will not work with this function!".format(game_id))

#This function sets the axis size to a fixed width/height within a figure
def set_axis_size (ax, w, h):
    if (not ax):
        return
    else:
        l = ax.figure.subplotpars.left
        r = ax.figure.subplotpars.right
        t = ax.figure.subplotpars.top
        b = ax.figure.subplotpars.bottom
        figw = float(w)/(r-l)
        figh = float(h)/(t-b)
        ax.figure.set_size_inches(figw, figh)

def fix_axes_size_incm(axew, axeh):
    axew = axew/2.54
    axeh = axeh/2.54

    #lets use the tight layout function to get a good padding size for our axes labels.
    fig = plot.gcf()
    ax = plot.gca()
    fig.tight_layout()
    #obtain the current ratio values for padding and fix size
    oldw, oldh = fig.get_size_inches()
    l = ax.figure.subplotpars.left
    r = ax.figure.subplotpars.right
    t = ax.figure.subplotpars.top
    b = ax.figure.subplotpars.bottom

    #work out what the new  ratio values for padding are, and the new fig size.
    neww = axew+oldw*(1-r+l)
    newh = axeh+oldh*(1-t+b)
    newr = r*oldw/neww
    newl = l*oldw/neww
    newt = t*oldh/newh
    newb = b*oldh/newh

    #right(top) padding, fixed axes size, left(bottom) pading
    hori = [Size.Scaled(newr), Size.Fixed(axew), Size.Scaled(newl)]
    vert = [Size.Scaled(newt), Size.Fixed(axeh), Size.Scaled(newb)]

    divider = Divider(fig, (0.0, 0.0, 1., 1.), hori, vert, aspect=False)
    # the width and height of the rectangle is ignored.

    ax.set_axes_locator(divider.new_locator(nx=1, ny=1))

    #we need to resize the figure now, as we have may have made our axes bigger than in.
    fig.set_size_inches(neww,newh)

def to_percent(y, position):
    # Ignore the passed in position. This has the effect of scaling the default
    # tick locations.
    s = str(round(100 * y, 1))

    # The percent symbol needs escaping in latex
    if matplotlib.rcParams['text.usetex'] is True:
        return s + r'$\%$'
    else:
        return s + '%'


def generate_unique_xvalues (y_vals, initial_x_offset, min_x_distance_allowed, min_y_distance_allowed, x_step_size = 0.1):
    y_vals = numpy.array(y_vals)
    x_vals = numpy.empty(len(y_vals)) * numpy.nan

    for i in range(0, len(y_vals)):
        x = initial_x_offset
        y = y_vals[i]

        y_dist = numpy.array(abs(y_vals - y)).astype(numpy.float32)
        y_dist[i] = numpy.nan
        are_any_within_range = any(y_dist < min_y_distance_allowed)
        if (are_any_within_range):
            idx_of_conflicting_points = numpy.where(y_dist < min_y_distance_allowed)[0]
            associated_x_values = x_vals[idx_of_conflicting_points]
            associated_x_values = associated_x_values[~numpy.isnan(associated_x_values)]

            if (len(associated_x_values) > 0):
                xt1 = initial_x_offset
                xt2 = initial_x_offset
                done = False

                while (not done):
                    xd1 = min(abs(associated_x_values - xt1))
                    xd2 = min(abs(associated_x_values - xt2))
                    if ((xd1 < min_x_distance_allowed) and (xd2 < min_x_distance_allowed)):
                        xt1 -= x_step_size
                        xt2 += x_step_size
                    else:
                        done = True
                        if (xd1 >= min_x_distance_allowed):
                            x = xt1
                        else:
                            x = xt2

        x_vals[i] = x
    
    return x_vals

def convert_restore_event_to_datetime (start_time_string, start_time_timestamp):
    event_datetime_from_string = datetime.strptime(start_time_string.strip(), "%H:%M:%S-%b-%d-%Y")
    event_datetime_from_timestamp = datetime.utcfromtimestamp(start_time_timestamp / 1000.0)
    result = event_datetime_from_string.replace(microsecond=event_datetime_from_timestamp.microsecond)
    return result



































