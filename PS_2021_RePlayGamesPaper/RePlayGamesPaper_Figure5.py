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
from RePlayAnalysisCore2.RePlayGameDataBreakout import RePlayGameDataBreakout
from RePlayAnalysisCore2.RePlayGameDataFruitArchery import RePlayGameDataFruitArchery
from RePlayAnalysisCore2.RePlayGameDataFruitNinja import RePlayGameDataFruitNinja
from RePlayAnalysisCore2.RePlayGameDataRepetitionsMode import RePlayGameDataRepetitionsMode
from RePlayAnalysisCore2.RePlayGameDataSpaceRunner import RePlayGameDataSpaceRunner
from RePlayAnalysisCore2.RePlayGameDataTrafficRacer import RePlayGameDataTrafficRacer
from RePlayAnalysisCore2.RePlayGameDataTyperShark import RePlayGameDataTyperShark
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

#Create a pandas dataframe that will hold the aggregate data for this figure
participant_data = pandas.DataFrame([], 
    columns = ["UID", 
    "Group", 
    "Breakout",
    "Breakout2", 
    "SpaceRunner", 
    "TrafficRacer",
    "FruitArchery",
    "FruitNinja",
    "TyperShark"])

# %%

#Get a starttime for the script
script_start_time = datetime.now()

#Iterate over every participant in the study
for current_participant in root.participants:
    #Skip this participant if the participant has been explicitly excluded
    if (current_participant.uid is None):
        continue
    if (not ("marked_for_exclusion" in current_participant.tags)):
        continue
    if (current_participant.tags["marked_for_exclusion"]):
        continue

    #Printer a header for this participant to the console
    print(f"Analyzing data for participant {Fore.GREEN}{str(current_participant.uid)}{Style.RESET_ALL}")

    #Create some empty arrays that will hold the data for this participant
    breakout_data = []
    breakout_data_2 = []
    spacerunner_data = []
    trafficracer_data = []
    fruitarchery_data = []
    fruitninja_data = []
    typershark_data = []

    #Determine the experimental group of this participant
    dfrow = root.participant_demographics_table.participants.loc[root.participant_demographics_table.participants["UID"] == current_participant.uid]
    try:
        hasbraininjury = dfrow["HasBrainInjury"].values[0]
    except:
        continue
    participant_group_id = "Control"
    if(hasbraininjury == "Y"):
        participant_group_id = "Injury"

    #Iterate over each visit for this participant
    for current_visit in current_participant.visits:
        #Check to see if this visit has been completely excluded
        if (current_visit.tags["marked_for_exclusion"]):
            continue

        #Determine if we should consider this visit for the purposes of this figure
        should_we_consider_this_visit = False
        if (not (current_visit.is_at_home_visit)):
            if ((current_visit.assignment_name == "Day 1") or (current_visit.assignment_name == "RePlay") or (current_visit.assignment_name == "Rx A: Mild")):
                should_we_consider_this_visit = True

        #Skip this visit if it has been determined we aren't using it for this figure
        if (not (should_we_consider_this_visit)):
            continue

        #Iterate over every activity of this visit
        for current_activity in current_visit.activities:
            #Skip this activity if it has been explicitly excluded
            if (current_activity.tags["marked_for_exclusion"]):
                continue

            if (current_activity.game_data is not None):
                if (current_activity.game_data.game_data is not None):
                    #Get the game data object from this activity
                    current_game_data = current_activity.game_data.game_data

                    #If this was a Breakout session...
                    if (isinstance(current_game_data, RePlayGameDataBreakout)):
                        (num_balls_lost, _, _, ball_loss_interval, _) = current_game_data.CalculateBreakoutGameMetrics()
                        breakout_data.append(ball_loss_interval)
                        breakout_data_2.append(num_balls_lost)
                    elif (isinstance(current_game_data, RePlayGameDataSpaceRunner)):
                        (_, _, attempt_durations, _, _) = current_game_data.CalculateSpaceRunnerMetrics()
                        spacerunner_data.extend(attempt_durations)
                    elif (isinstance(current_game_data, RePlayGameDataTrafficRacer)):
                        percent_time_in_target_lane = current_game_data.CalculatePercentTimeInTargetLane()
                        trafficracer_data.append(percent_time_in_target_lane)
                    elif (isinstance(current_game_data, RePlayGameDataFruitArchery)):
                        fruit_hit_per_minute = current_game_data.CalculateFruitHitPerMinute()
                        fruitarchery_data.append(fruit_hit_per_minute)
                    elif (isinstance(current_game_data, RePlayGameDataFruitNinja)):
                        swipe_accuracy = current_game_data.CalculateSwipeAccuracy()
                        fruitninja_data.append(swipe_accuracy)
                    elif (isinstance(current_game_data, RePlayGameDataTyperShark)):
                        (_, _, _, _, _, _, words_per_minute, _, _, _, _) = current_game_data.CalculateTyperSharkMetrics()
                        typershark_data.append(words_per_minute)

    #Calculate the mean statistic for each game for this participant
    breakout_mean = numpy.nanmean(breakout_data)
    breakout2_mean = numpy.nanmean(breakout_data_2)
    spacerunner_mean = numpy.nanmean(spacerunner_data)
    trafficracer_mean = numpy.nanmean(trafficracer_data)
    fruitarchery_mean = numpy.nanmean(fruitarchery_data)
    fruitninja_mean = numpy.nanmean(fruitninja_data)
    typershark_mean = numpy.nanmean(typershark_data)

    #Add a row representing this participant to the participant dataframe
    participant_data = participant_data.append({
        "UID" : current_participant.uid, 
        "Group" : participant_group_id,
        "Breakout" : breakout_mean,
        "Breakout2" : breakout2_mean, 
        "SpaceRunner" : spacerunner_mean, 
        "TrafficRacer" : trafficracer_mean,
        "FruitArchery" : fruitarchery_mean,
        "FruitNinja" : fruitninja_mean,
        "TyperShark" : typershark_mean 
        }, ignore_index = True)

# %%

# Now let's define a method that we will use to create our bar plots
def create_plot_2group (participant_data, variable_to_plot, plot_y_label, plot_title, ymin, ymax, figure_path):
    #Divide into groups
    stats_data = participant_data[participant_data[variable_to_plot].notna()]
    control_subjects = stats_data[stats_data["Group"] == "Control"] 
    all_noncontrol_subjects = stats_data[stats_data["Group"] != "Control"]

    #Now let's do a simple t-test between control and stroke subjects
    (t, p) = stats.ttest_ind(control_subjects[variable_to_plot], all_noncontrol_subjects[variable_to_plot])
    print(f"{variable_to_plot}, T-test between Control vs Injury: t = {t}, p = {p}")
    
    control_mean = control_subjects[variable_to_plot].mean()
    control_err = control_subjects[variable_to_plot].sem()
    all_noncontrol_mean = all_noncontrol_subjects[variable_to_plot].mean()
    all_noncontrol_err = all_noncontrol_subjects[variable_to_plot].sem()
    print(f"Control: {control_mean} +/- {control_err}")
    print(f"Injury mean: {all_noncontrol_mean} +/- {all_noncontrol_err}")
    print("")         

    #Now let's plot controls vs non-controls
    plot.figure()
    plot.bar([1, 2], 
            [control_mean, all_noncontrol_mean], 
            yerr = [control_err, all_noncontrol_err], 
            color = ["#1F77B4", "#DB4437"],
            width = 0.5, error_kw=dict(lw=3, capsize=5, capthick=3))
    ax1 = plot.gca()

    #Now plot each individual
    numpy_stats_data = numpy.array(stats_data[variable_to_plot])
    control_data = numpy.array(control_subjects[variable_to_plot])
    non_control_data = numpy.array(all_noncontrol_subjects[variable_to_plot])

    #Figure out how far apart we want points to be spaced
    minpoint = numpy.nanmin(numpy_stats_data)
    maxpoint = numpy.nanmax(numpy_stats_data)
    (cur_ymin, cur_ymax) = plot.ylim()
    overallmin = numpy.min([minpoint, maxpoint, cur_ymin, cur_ymax])
    overallmax = numpy.max([minpoint, maxpoint, cur_ymin, cur_ymax])
    overallrange = overallmax - overallmin
    min_y_distance_between_points = 0.05 * overallrange

    control_xdata = RePlayUtilities.generate_unique_xvalues(
        control_data, 0, 0.1, min_y_distance_between_points, 0.1)
    control_xdata += numpy.abs(numpy.nanmin(control_xdata)) + 0.4

    non_control_xdata = RePlayUtilities.generate_unique_xvalues(
        non_control_data, 0, 0.1, min_y_distance_between_points, 0.1)
    non_control_xdata += numpy.abs(numpy.nanmin(non_control_xdata)) + 2.33
    max_x_needed = numpy.nanmax(non_control_xdata) + 0.25

    plot.plot(control_xdata, control_data, marker = 'o', linestyle = 'None', color = 'k', markerfacecolor = 'k', markersize = 8)
    plot.plot(non_control_xdata, non_control_data, marker = 'o', linestyle = 'None', color = 'k', markerfacecolor = 'k', markersize = 8)
    plot.xlim([0.25, max_x_needed])
    plot.xticks([1, 2])
    #ax1.set_xticklabels(["Control", "Injury"])
    ax1.set_xticklabels(["", ""])
    #plot.ylabel(plot_y_label)
    plot.ylim([ymin, ymax])
    
    #Save the figure
    full_figure_path = figure_path + f"replay_day1_{variable_to_plot}.png"
    plot.savefig(full_figure_path, dpi=300)    
    full_figure_path = figure_path + f"replay_day1_{variable_to_plot}.svg"
    plot.savefig(full_figure_path, dpi=300)

    #plot.show()



# %%

# Now let's plot each game - Controls vs Injury

# Breakout
create_plot_2group (participant_data, "Breakout", "Time between ball loss (s)", "Breakout", 0, 120, figure_path)
create_plot_2group (participant_data, "Breakout2", "Time between ball loss (s)", "Breakout: num balls lost", 0, 120, figure_path)
create_plot_2group (participant_data, "SpaceRunner", "Duration of attempt (s)", "Space Runner", 0, 160, figure_path)
create_plot_2group (participant_data, "TrafficRacer", "Percent time in target lane", "Traffic Racer", 0, 100, figure_path)
create_plot_2group (participant_data, "FruitArchery", "Fruit hit per minute", "Fruit Archery", 0, 20, figure_path)
create_plot_2group (participant_data, "FruitNinja", "Swipe accuracy", "Fruit Ninja", 0, 100, figure_path)
create_plot_2group (participant_data, "TyperShark", "Words per minute", "Typer Shark", 0, 16, figure_path)

# %%
