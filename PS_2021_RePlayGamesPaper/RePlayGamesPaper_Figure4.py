# %%
import sys
import os.path as o
sys.path.append(o.abspath(o.join(o.dirname(sys.modules[__name__].__file__), "..")))


# %%
#region imports and setup

import ZODB
import ZODB.FileStorage
import transaction
import pandas
import numpy
import persistent

from datetime import datetime
from datetime import timedelta
from dateutil import parser
import statistics
import math
import matplotlib.pyplot as plot
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
from scipy import stats
import statsmodels.stats.multicomp

import os
from os import walk
from os import listdir
from os.path import isfile, join
from pathlib import Path

from tkinter import filedialog
from tkinter import Tk

from colorama import Fore
from colorama import Style
import colorama

from RePlayAnalysisCore2.ParticipantDemographics import ParticipantDemographics
from RePlayAnalysisCore2.VisitsTable import VisitsTable
from RePlayAnalysisCore2.ReadGoogleSpreadsheet import GoogleSheets
from RePlayAnalysisCore2.RePlayAnalysisConfiguration import RePlayAnalysisConfiguration
from RePlayAnalysisCore2.RePlayGUI import RePlayGUI
from RePlayAnalysisCore2.RePlayDataFile import RePlayDataFile
from RePlayAnalysisCore2.RePlayActivity import RePlayActivity
from RePlayAnalysisCore2.RePlayParticipant import RePlayParticipant
from RePlayAnalysisCore2.RePlayVisit import RePlayVisit
from RePlayAnalysisCore2.RePlaySignalAnalyzer import RePlaySignalAnalyzer
from RePlayAnalysisCore2 import RePlayUtilities

#Initialize colorama
colorama.init()

#Ask the user for the location of the RePlay data files
RePlayGUI.InitializeGUI()
RePlayAnalysisConfiguration.ReadConfigurationFile(True)
replay_data_location = RePlayAnalysisConfiguration.box_folder_location
db_path = RePlayAnalysisConfiguration.database_location

#Create or fetch the database file, and open a connection to the database
storage = ZODB.FileStorage.FileStorage("replay_games_paper_db.fs")
db = ZODB.DB(storage)
db_connection = db.open()
root = db_connection.root

#Define a couple of things that will be used later in the script when it comes time to save figures
current_date_str = datetime.now().strftime("%Y_%m_%d")
figure_path = RePlayAnalysisConfiguration.figure_saving_location + f"/{current_date_str}/"
Path(figure_path).mkdir(parents=True, exist_ok=True)

#define the tag used to hold metadata for this figure
this_script_tag = "PS_2021_RePlayGamesPaper_Figure4_Metadata"
refresh_all_metadata = False

#Create a structure to store the summary data
participant_data = pandas.DataFrame([], columns = [
    "UID", 
    "Group",
    "InjuryType",
    "RepsDay1", 
    "RepsAtHomeDaily",
    "RepsAtHome",
    "SessionDurationDay1",
    "SessionDurationAtHomeDaily",
    "SessionDurationAtHome",
    "PercentTimeMovingDay1",
    "PercentTimeMovingAtHomeDaily",
    "PercentTimeMovingAtHome"])

#endregion

# %%    
#region data analysis - count reps

#Get a starttime for the script
script_start_time = datetime.now()
debuging_mode = True

for current_participant in root.participants:
    if (current_participant.uid is None):
        continue
    if (not ("marked_for_exclusion" in current_participant.tags)):
        continue
    if (current_participant.tags["marked_for_exclusion"]):
        continue

    #Printer a header for this participant to the console
    print(f"Analyzing data for participant {Fore.GREEN}{str(current_participant.uid)}{Style.RESET_ALL}", end = "")

    dfrow = root.participant_demographics_table.participants.loc[root.participant_demographics_table.participants["UID"] == current_participant.uid]
    injury_type = dfrow["InjuryType"].values[0]
    print(f" ({injury_type})")
    try:
        hasbraininjury = dfrow["HasBrainInjury"].values[0]
    except:
        continue
    participant_group_id = "Control"
    if(hasbraininjury == "Y"):
        participant_group_id = "Injury"
        
    this_participant_repsday1 = 0
    this_participant_repsathomedaily = []
    this_participant_repsathome = 0
    this_participant_durationday1 = 0
    this_participant_durationathomedaily = []
    this_participant_durationathome = 0
    this_participant_total_time_active_day1 = 0
    this_participant_percentactiveday1 = 0
    this_participant_percentactiveathomedaily = []
    this_participant_percentactiveathome = 0

    for current_visit in current_participant.visits:
        if (current_visit.tags["marked_for_exclusion"]):
            continue

        should_we_consider_this_visit = True
        if (not (current_visit.is_at_home_visit)):
            if ((current_visit.assignment_name == "Day 1") or (current_visit.assignment_name == "RePlay") or (current_visit.assignment_name == "Rx A: Mild")):
                should_we_consider_this_visit = True
            else:
                should_we_consider_this_visit = False

        if (not (should_we_consider_this_visit)):
            continue

        this_visit_total_reps = []
        this_visit_total_time_active = []
        this_visit_total_time = []

        this_visit_dates = current_visit.GetDatesInRangeOfVisit(current_visit.is_at_home_visit)
        for current_date in this_visit_dates:
            this_date_activities = current_visit.GetActivitiesOnDate(current_date)

            this_date_total_reps = 0
            this_date_total_time_active = 0
            this_date_total_time = 0

            for current_activity in this_date_activities:
                #If this activity is marked for exclusion, then skip it
                if (current_activity.tags["marked_for_exclusion"]):
                    continue

                #Instantiate some variables to hold data for this session
                this_session_duration = 0
                this_session_total_reps = 0
                this_session_time_moving = timedelta(seconds = 0)

                #If metadata for this session has not previously been calculated, OR
                #if the user of this script wants to re-calculate the data, then...
                if ((this_script_tag not in current_activity.tags) or (refresh_all_metadata)):
                    
                    #Grab the session duration
                    if (current_activity.game_data is not None):
                        if (current_activity.game_data.game_data is not None):
                            if ((current_activity.game_data.game_data.signal_time is not None) and 
                                (len(current_activity.game_data.game_data.signal_time) > 0)):
                                this_session_duration = current_activity.game_data.game_data.signal_time[-1]
                                if (math.isnan(this_session_duration)):
                                    this_session_duration = 0
                                elif (math.isinf(this_session_duration)):
                                    this_session_duration = 0

                    #Grab the repetition data for this session
                    (this_session_total_reps, _, this_session_time_moving, _) = current_activity.GetRepetitionData()

                    #Add metadata about this current activity to the database
                    if (this_script_tag not in current_activity.tags):
                        current_activity.tags[this_script_tag] = persistent.mapping.PersistentMapping()
                    current_activity.tags[this_script_tag]["this_session_duration"] = this_session_duration
                    current_activity.tags[this_script_tag]["this_session_total_reps"] = this_session_total_reps
                    current_activity.tags[this_script_tag]["this_session_time_moving"] = this_session_time_moving
                    transaction.commit()
                else:
                    #If we reach this piece of code, it means that metadata has previously been calculated
                    #for this session, AND the user doesn't want to re-calculate it. Therefore, we will use
                    #the previously calculated metadata. This will increase the speed of running the script.
                    this_session_duration = current_activity.tags[this_script_tag]["this_session_duration"]
                    this_session_total_reps = current_activity.tags[this_script_tag]["this_session_total_reps"]
                    this_session_time_moving = current_activity.tags[this_script_tag]["this_session_time_moving"]

                #Add the data for this session to the data for the current date
                this_date_total_reps += this_session_total_reps
                this_date_total_time_active += this_session_time_moving.total_seconds()
                this_date_total_time += this_session_duration
                
            this_visit_total_reps.append(this_date_total_reps)
            this_visit_total_time_active.append(this_date_total_time_active)
            this_visit_total_time.append(this_date_total_time)
        
        this_visit_total_reps_per_day = numpy.nanmean(this_visit_total_reps)
        this_visit_total_time_per_day = numpy.nanmean(this_visit_total_time)
        this_visit_percent_active_time_each_day = []
        for i in range(0, len(this_visit_total_time)):
            if (this_visit_total_time[i] != 0):
                pta = 100 * (this_visit_total_time_active[i] / this_visit_total_time[i])
            else:
                pta = float("NaN")
            this_visit_percent_active_time_each_day.append(pta)
        
        this_visit_percent_active_time_each_day = numpy.array(this_visit_percent_active_time_each_day)
        this_visit_percent_active_time_each_day = this_visit_percent_active_time_each_day[~numpy.isnan(this_visit_percent_active_time_each_day)]
        if (len(this_visit_percent_active_time_each_day) > 0):
            this_visit_percent_active_time_per_day = numpy.nanmean(this_visit_percent_active_time_each_day)
        else:
            this_visit_percent_active_time_per_day = 0

        if (len(this_visit_total_time_active) > 0):
            this_visit_total_time_active_summed = numpy.nansum(this_visit_total_time_active)
        else:
            this_visit_total_time_active_summed = 0

        if (current_visit.is_at_home_visit):
            this_participant_repsathomedaily = this_visit_total_reps
            this_participant_repsathome = this_visit_total_reps_per_day
            this_participant_durationathomedaily = this_visit_total_time
            this_participant_durationathome = this_visit_total_time_per_day
            this_participant_percentactiveathomedaily = this_visit_percent_active_time_each_day
            this_participant_percentactiveathome = this_visit_percent_active_time_per_day        
        else:
            this_participant_repsday1 += this_visit_total_reps_per_day
            this_participant_durationday1 += this_visit_total_time_per_day
            this_participant_total_time_active_day1 += this_visit_total_time_active_summed

    try:
        if (this_participant_durationday1 < 0.1):
            this_participant_percentactiveday1 = 0
        else:
            this_participant_percentactiveday1 = (this_participant_total_time_active_day1 / this_participant_durationday1) * 100.0
    except:
        this_participant_percentactiveday1 = 0

    participant_data = participant_data.append({
        "UID" : current_participant.uid, 
        "Group" : participant_group_id,
        "InjuryType" : injury_type,
        "RepsDay1" : this_participant_repsday1, 
        "RepsAtHomeDaily" : this_participant_repsathomedaily,
        "RepsAtHome" : this_participant_repsathome,
        "SessionDurationDay1" : this_participant_durationday1,
        "SessionDurationAtHomeDaily" : this_participant_durationathomedaily,
        "SessionDurationAtHome" : this_participant_durationathome,
        "PercentTimeMovingDay1" : this_participant_percentactiveday1,
        "PercentTimeMovingAtHomeDaily" : this_participant_percentactiveathomedaily,
        "PercentTimeMovingAtHome" : this_participant_percentactiveathome
        }, ignore_index = True)

script_end_time = datetime.now()
script_running_time = script_end_time - script_start_time
print(f"Running duration of script: {script_running_time}")
print("")

#endregion

# %%
#region close the database connection


#Close the connection to the database
db_connection.close()       

#endregion

# %%
#region prepare first plot and statistics

#Plot 1 - Controls vs non-controls, total repetitions
control_subjects = participant_data[participant_data["Group"] == "Control"] 
all_noncontrols = participant_data[participant_data["Group"] != "Control"]
in_clinic_subjects = all_noncontrols[all_noncontrols["RepsDay1"] >= 1]
takehome_subjects = all_noncontrols[all_noncontrols["RepsAtHome"] >= 1]
injury_group_both_settings = all_noncontrols[(all_noncontrols["RepsDay1"] >= 1) & (all_noncontrols["RepsAtHome"] >= 1)]

in_clinic_subjects_tbi_flag = []
takehome_subjects_tbi_flag = []
for _,p in participant_data.iterrows():
    if((p["Group"] != "Control") and (p["InjuryType"] is not None)):
        if (p["RepsDay1"] >= 1):
            if (p["InjuryType"] == "TBI"):
                in_clinic_subjects_tbi_flag.append(1)
            else:
                in_clinic_subjects_tbi_flag.append(0)
        if (p["RepsAtHome"] >= 1):
            if (p["InjuryType"] == "TBI"):
                takehome_subjects_tbi_flag.append(1)
            else:
                takehome_subjects_tbi_flag.append(0)

group_list = ["Control", "Injury: in clinic", "Injury: at home"]
colors_for_groups = ["#4285F4", "#DB4437", "#F4B400", "#0F9D58"]

control_subjects_mean = control_subjects["RepsDay1"].mean()
control_subjects_err = control_subjects["RepsDay1"].sem()
in_clinic_subjects_mean = in_clinic_subjects["RepsDay1"].mean()
in_clinic_subjects_err = in_clinic_subjects["RepsDay1"].sem()
takehome_subjects_mean = takehome_subjects["RepsAtHome"].mean()
takehome_subjects_err = takehome_subjects["RepsAtHome"].sem()

#Let's do some stats. Divide into groups
control_subjects_stats_data = control_subjects[control_subjects["RepsDay1"].notna()]
in_clinic_subjects_stats_data = in_clinic_subjects[in_clinic_subjects["RepsDay1"].notna()]
takehome_subjects_stats_data = takehome_subjects[takehome_subjects["RepsAtHome"].notna()]
injury_group_both_settings_stats_data = injury_group_both_settings[(injury_group_both_settings["RepsDay1"].notna()) & (injury_group_both_settings["RepsAtHome"].notna())]

#Print some summary information
print(f"Control subjects (day 1 repetitions): {control_subjects_mean} +/- {control_subjects_err}")
print(f"In-clinic subjects subjects (day 1 repetitions): {in_clinic_subjects_mean} +/- {in_clinic_subjects_err}")
print(f"At-home subjects subjects (repetitions per day): {takehome_subjects_mean} +/- {takehome_subjects_err}")

#Now let's do a simple t-test between control and stroke subjects
(t, p) = stats.ttest_ind(control_subjects_stats_data["RepsDay1"], in_clinic_subjects["RepsDay1"])
print(f"UNPAIRED T-test between Controls vs Injury group (in clinic): t = {t:.3f}, p = {p:.3f}")

#Now let's do a paired t-test between takehome in-clinic and takehome at-home
(t, p) = stats.ttest_ind(in_clinic_subjects["RepsDay1"], takehome_subjects_stats_data["RepsAtHome"])
print(f"UNPAIRED T-test between Injury group (in clinic) vs Injury group (at home): t = {t:.3f}, p = {p:.3f}")

#Now let's do a paired t-test between takehome in-clinic and takehome at-home
(t, p) = stats.ttest_rel(injury_group_both_settings["RepsDay1"], injury_group_both_settings["RepsAtHome"])
print(f"PAIRED T-test between Injury group (in clinic) vs Injury group (at home): t = {t:.3f}, p = {p:.3f}")

#endregion

# %%
#region plot the first plot

plot.figure()
plot.bar(
    [1, 2, 3.7], 
    [control_subjects_mean, in_clinic_subjects_mean, takehome_subjects_mean],
    yerr = [control_subjects_err, in_clinic_subjects_err, takehome_subjects_err],
    color = [colors_for_groups[0], colors_for_groups[1], colors_for_groups[2]],
    width = 0.5,
    error_kw=dict(lw=3, capsize=5, capthick=3)
    )

y_values = numpy.array(control_subjects["RepsDay1"])
x_values = RePlayUtilities.generate_unique_xvalues(y_values, 1.5, 0.1, 50, 0.03)
for i in range(0, len(x_values)):
    xval = x_values[i]
    yval = y_values[i]
    plot.plot(xval, yval, marker = 'o', linestyle = 'None', color = 'k', markerfacecolor = 'k', markersize = 8)

uids = in_clinic_subjects["UID"]
y_values = numpy.array(in_clinic_subjects["RepsDay1"])
x_values = RePlayUtilities.generate_unique_xvalues(y_values, 2.7, 0.1, 100, 0.03)
for i in range(0, len(x_values)):
    xval = x_values[i]
    yval = y_values[i]
    cur_color = 'k'
    this_uid = uids.iloc[i]
    if (any(injury_group_both_settings["UID"] == this_uid)):
        cur_color = "#F4B400"
    is_tbi = in_clinic_subjects_tbi_flag[i]
    marker_to_use = 'o'
    if (is_tbi):
        marker_to_use = '^'        
    plot.plot(xval, yval, marker = marker_to_use, linestyle = 'None', color = 'k', markerfacecolor = cur_color, markersize = 8)

uids = takehome_subjects["UID"]
y_values = numpy.array(takehome_subjects["RepsAtHome"])
x_values = RePlayUtilities.generate_unique_xvalues(y_values, 4.2, 0.1, 100, 0.03)
for i in range(0, len(x_values)):
    xval = x_values[i]
    yval = y_values[i]
    this_uid = uids.iloc[i]
    cur_color = 'k'
    if (any(injury_group_both_settings["UID"] == this_uid)):
        cur_color = "#F4B400"
    is_tbi = takehome_subjects_tbi_flag[i]
    marker_to_use = 'o'
    if (is_tbi):
        marker_to_use = '^'        
    plot.plot(xval, yval, marker = marker_to_use, linestyle = 'None', color = 'k', markerfacecolor = cur_color, markersize = 8)

plot.axhline(100, linestyle = '--', color = 'k')

axes = plot.gca()
axes.set_xticks([1, 2, 3.7])
axes.set_xticklabels(["Control", "Injury (in clinic)", "Injury (at home)"])
plot.xlim([0.5, 4.5])
plot.ylabel("Daily Repetitions")
plot.ylim([0, 2500])

#Save the figure
full_figure_path = figure_path + "replay_combined_total_reps_v0.png"
plot.savefig(full_figure_path)
full_figure_path = figure_path + "replay_combined_total_reps_v0.svg"
plot.savefig(full_figure_path)    

#plot.show()
plot.close()

#endregion

# %%
#region prepare second plot and statistics

control_subjects = participant_data[participant_data["Group"] == "Control"] 
all_noncontrols = participant_data[participant_data["Group"] != "Control"]
in_clinic_subjects = all_noncontrols[all_noncontrols["PercentTimeMovingDay1"] >= 1]
takehome_subjects = all_noncontrols[all_noncontrols["PercentTimeMovingAtHome"] >= 1]
injury_group_both_settings = all_noncontrols[(all_noncontrols["PercentTimeMovingDay1"] >= 1) & (all_noncontrols["PercentTimeMovingAtHome"] >= 1)]

in_clinic_subjects_tbi_flag = []
takehome_subjects_tbi_flag = []
for _,p in participant_data.iterrows():
    if((p["Group"] != "Control") and (p["InjuryType"] is not None)):
        if (p["PercentTimeMovingDay1"] >= 1):
            if (p["InjuryType"] == "TBI"):
                in_clinic_subjects_tbi_flag.append(1)
            else:
                in_clinic_subjects_tbi_flag.append(0)
        if (p["PercentTimeMovingAtHome"] >= 1):
            if (p["InjuryType"] == "TBI"):
                takehome_subjects_tbi_flag.append(1)
            else:
                takehome_subjects_tbi_flag.append(0)

group_list = ["Control", "Injury: in clinic", "Injury: at home"]
colors_for_groups = ["#4285F4", "#DB4437", "#F4B400", "#0F9D58"]

control_subjects_mean = control_subjects["PercentTimeMovingDay1"].mean()
control_subjects_err = control_subjects["PercentTimeMovingDay1"].sem()
in_clinic_subjects_mean = in_clinic_subjects["PercentTimeMovingDay1"].mean()
in_clinic_subjects_err = in_clinic_subjects["PercentTimeMovingDay1"].sem()
takehome_subjects_mean = takehome_subjects["PercentTimeMovingAtHome"].mean()
takehome_subjects_err = takehome_subjects["PercentTimeMovingAtHome"].sem()

#Let's do some stats. Divide into groups
control_subjects_stats_data = control_subjects[control_subjects["PercentTimeMovingDay1"].notna()]
in_clinic_subjects_stats_data = in_clinic_subjects[in_clinic_subjects["PercentTimeMovingDay1"].notna()]
takehome_subjects_stats_data = takehome_subjects[takehome_subjects["PercentTimeMovingAtHome"].notna()]
injury_group_both_settings_stats_data = injury_group_both_settings[(injury_group_both_settings["PercentTimeMovingDay1"].notna()) & (injury_group_both_settings["RepsAtHome"].notna())]

#Print some summary information
print(f"Control subjects (day 1 percent time moving): {control_subjects_mean} +/- {control_subjects_err}")
print(f"In-clinic subjects subjects (day 1 percent time moving): {in_clinic_subjects_mean} +/- {in_clinic_subjects_err}")
print(f"At-home subjects subjects (percent time moving per day): {takehome_subjects_mean} +/- {takehome_subjects_err}")

#Now let's do a simple t-test between control and stroke subjects
(t, p) = stats.ttest_ind(control_subjects_stats_data["PercentTimeMovingDay1"], in_clinic_subjects["PercentTimeMovingDay1"])
print(f"UNPAIRED T-test between Controls vs Injury group (in clinic): t = {t:.3f}, p = {p:.3f}")

#Now let's do a paired t-test between takehome in-clinic and takehome at-home
(t, p) = stats.ttest_ind(in_clinic_subjects["PercentTimeMovingDay1"], takehome_subjects_stats_data["PercentTimeMovingAtHome"])
print(f"UNPAIRED T-test between Injury group (in clinic) vs Injury group (at home): t = {t:.3f}, p = {p:.3f}")

#Now let's do a paired t-test between takehome in-clinic and takehome at-home
(t, p) = stats.ttest_rel(injury_group_both_settings["PercentTimeMovingDay1"], injury_group_both_settings["PercentTimeMovingAtHome"])
print(f"PAIRED T-test between Injury group (in clinic) vs Injury group (at home): t = {t:.3f}, p = {p:.3f}")

#endregion

# %%
#region plot the second plot

plot.figure()
plot.bar(
    [1, 2, 3.7], 
    [control_subjects_mean, in_clinic_subjects_mean, takehome_subjects_mean],
    yerr = [control_subjects_err, in_clinic_subjects_err, takehome_subjects_err],
    color = [colors_for_groups[0], colors_for_groups[1], colors_for_groups[2]],
    width = 0.5,
    error_kw=dict(lw=3, capsize=5, capthick=3)
    )

y_values = numpy.array(control_subjects["PercentTimeMovingDay1"])
x_values = RePlayUtilities.generate_unique_xvalues(y_values, 1.45, 0.1, 5, 0.03)
for i in range(0, len(x_values)):
    xval = x_values[i]
    yval = y_values[i]
    plot.plot(xval, yval, marker = 'o', linestyle = 'None', color = 'k', markerfacecolor = 'k', markersize = 8)

uids = in_clinic_subjects["UID"]
y_values = numpy.array(in_clinic_subjects["PercentTimeMovingDay1"])
x_values = RePlayUtilities.generate_unique_xvalues(y_values, 2.8, 0.1, 5, 0.03)
for i in range(0, len(x_values)):
    xval = x_values[i]
    yval = y_values[i]
    cur_color = 'k'
    this_uid = uids.iloc[i]
    if (any(injury_group_both_settings["UID"] == this_uid)):
        cur_color = "#F4B400"
    is_tbi = in_clinic_subjects_tbi_flag[i]
    marker_to_use = 'o'
    if (is_tbi):
        marker_to_use = '^'         
    plot.plot(xval, yval, marker = marker_to_use, linestyle = 'None', color = 'k', markerfacecolor = cur_color, markersize = 8)

uids = takehome_subjects["UID"]
y_values = numpy.array(takehome_subjects["PercentTimeMovingAtHome"])
x_values = RePlayUtilities.generate_unique_xvalues(y_values, 4.3, 0.1, 5, 0.03)
for i in range(0, len(x_values)):
    xval = x_values[i]
    yval = y_values[i]
    this_uid = uids.iloc[i]
    cur_color = 'k'
    if (any(injury_group_both_settings["UID"] == this_uid)):
        cur_color = "#F4B400"
    is_tbi = takehome_subjects_tbi_flag[i]
    marker_to_use = 'o'
    if (is_tbi):
        marker_to_use = '^'         
    plot.plot(xval, yval, marker = marker_to_use, linestyle = 'None', color = 'k', markerfacecolor = cur_color, markersize = 8)

#plot.axhline(100, linestyle = '--', color = 'k')

axes = plot.gca()
axes.set_xticks([1, 2, 3.7])
axes.set_xticklabels(["Control", "Injury (in clinic)", "Injury (at home)"])
plot.xlim([0.5, 4.5])
plot.ylabel("Percent time actively moving")
plot.ylim([0, 100])

#Save the figure
full_figure_path = figure_path + "replay_combined_percent_moving_v0.png"
plot.savefig(full_figure_path)
full_figure_path = figure_path + "replay_combined_percent_moving_v0.svg"
plot.savefig(full_figure_path)    

#plot.show()
plot.close()


#endregion
# %%

#Print information about the at-home session duration
takehome_subjects = all_noncontrols[all_noncontrols["SessionDurationAtHome"] >= 1]
takehome_subjects_mean = takehome_subjects["SessionDurationAtHome"].mean()
takehome_subjects_err = takehome_subjects["SessionDurationAtHome"].sem()

print(f"At-home subjects subjects (daily session duration): {takehome_subjects_mean / 60} +/- {takehome_subjects_err / 60}")
# %%
