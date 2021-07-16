##########################################################
# Author: David Pruitt
# Original creation date: 28 January 2021
# 
# Purpose: This script loads data into the ZODB object-oriented
#   database.
#
# Important information: This script runs in 5 "phases". Before you run
#   this script, it is a good idea to think about which phases
#   you actually need to run for your purposes. Information about each
#   of the phases can be found below.
#
##########################################################

# %%
import sys
import os.path as o
sys.path.append(o.abspath(o.join(o.dirname(sys.modules[__name__].__file__), "..")))


# %%

import ZODB
import ZODB.FileStorage
import transaction
import persistent
import pandas

import os
from os import walk
from os import listdir
from os.path import isfile, join
from pathlib import Path

from tkinter import filedialog
from tkinter import Tk

import traceback
from datetime import datetime


from RePlayAnalysisCore2.ParticipantDemographics import ParticipantDemographics
from RePlayAnalysisCore2.VisitsTable import VisitsTable
from RePlayAnalysisCore2.LoadedFilesTable import LoadedFilesTable
from RePlayAnalysisCore2.ReadGoogleSpreadsheet import GoogleSheets
from RePlayAnalysisCore2.RePlayAnalysisConfiguration import RePlayAnalysisConfiguration
from RePlayAnalysisCore2.RePlayGUI import RePlayGUI
from RePlayAnalysisCore2.RePlayDataFile import RePlayDataFile
from RePlayAnalysisCore2.RePlayActivity import RePlayActivity
from RePlayAnalysisCore2.RePlayParticipant import RePlayParticipant
from RePlayAnalysisCore2.RePlayVisit import RePlayVisit
from RePlayAnalysisCore2 import RePlayUtilities

#Flags to determine which phases of this script to execute
ExecutePhase1 = True        #Phase 1: Update the participant demographics table and the visits table from Google or RedCap
ExecutePhase2 = True        #Phase 2: Load raw data files (this part takes the longest)
ExecutePhase3 = True        #Phase 3: Add participants to the object tree structure if they are not already in it
ExecutePhase4 = True        #Phase 4: Add visits to the object tree structure if they are not already in it
ExecutePhase5 = True        #Phase 5: Find any activities that do not have a parent visit and match them with a parent visit

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

#Initialize the google sheets service
GoogleSheets.InitializeGoogleSheets()

#Create the participant data and visit data objects
if not(hasattr(root, 'participant_demographics_table')):
    root.participant_demographics_table = ParticipantDemographics()
if not(hasattr(root, 'visits_table')):
    root.visits_table = VisitsTable()
if not(hasattr(root, 'loaded_files')):
    root.loaded_files = LoadedFilesTable()
if not(hasattr(root, 'activity_list')):
    root.activity_list = persistent.list.PersistentList()
if not(hasattr(root, 'participants')):
    root.participants = persistent.list.PersistentList()

if not(hasattr(root, "name")):
    root.name = "RePlay Usability Study: \"RePlay Games Paper\""
if not(hasattr(root, "last_update")):
    root.last_update = datetime.utcnow()

#Set the "last update" timestamp on the database to be the current date/time
root.last_update = datetime.utcnow()

#region Phase 1
# %%

if ExecutePhase1:

    #Update the participant data
    sheet_id = "19Lbdkeljuk6lDtG5-Z0VoH6SMbIv35ZgjLYzFK2xvwM"
    tab_name = "ParticipantMetaRePlay"
    root.participant_demographics_table.LoadParticipantDemographicsFromGoogle(sheet_id, tab_name)

    #Update the visit data
    tab_name = "VisitMeta"
    root.visits_table.LoadVisitsTableFromGoogle(sheet_id, tab_name)

    #Commit the transaction to the database
    print("Committing phase 1 changes...", end = "")
    transaction.commit()
    print("Complete")

#endregion

#region Phase 2
# %%

if ExecutePhase2:

    #Walk the directory tree and find all relevant files
    print ("Walking the directory tree to find relevant files...")
    f = []
    for replay_data_location_x in replay_data_location:
        for (dirpath, _, filenames) in walk(replay_data_location_x):
            for fn in filenames:
                f.extend([[dirpath, fn]])

    print("Loading files into the database...")
    #If files were found, let's check to see if they exist in the database already
    loaded_previously = 0
    loaded_successfully = 0
    loaded_unrecognized = 0
    loaded_failed = 0
    loaded_db_failed = 0
    if len(f) > 0:
        #Iterate through each file that was found...
        for this_file in f:
            #Make sure the file we are checking is the correct file type...
            if this_file[1].lower().endswith(".txt"):

                #Do an initial read of the file's metadata
                this_full_file_path = this_file[0] + "/" + this_file[1]
                success = False
                try:
                    this_file_data = RePlayDataFile(this_full_file_path)
                    success = True
                except:
                    print ("THIS FILE DOESN'T LOOK LIKE A REPLAY FILE: " + this_file[1])
                    loaded_unrecognized = loaded_unrecognized + 1
                
                if success:
                    #Grab the participant id from the file
                    participant_id = this_file_data.subject_id

                    #Check to see if this file has already been loaded into the database
                    already_loaded = root.loaded_files.IsFileAlreadyLoaded(this_file[1], this_file_data.md5_checksum)

                    if not already_loaded:
                        #If the file has not already been loaded, try to load the file's
                        #data into memory
                        try:
                            #Read the whole file
                            this_file_data.ReadData()

                            #Add this file to the list of loaded files
                            root.loaded_files.AppendLoadedFileToTable(participant_id, this_file[1], this_file_data.md5_checksum)

                            #Update the list of activities
                            RePlayActivity.AddSessionToActivityList(root.activity_list, this_file_data)
                            
                            print("Successfully loaded file: " + this_file[1], end = "")
                            loaded_successfully = loaded_successfully + 1

                            #Commit the transaction to the database
                            transaction.commit()
                            print (" (Partial commit complete)")
                        except Exception as e:
                            traceback.print_exc()
                            print(e.__class__)
                            print("FAILED TO LOAD FILE: " + this_file[1])
                            loaded_failed = loaded_failed + 1

                    else:
                        print(this_file[1] + " was previously loaded into the database.")    
                        loaded_previously = loaded_previously + 1                                                            
                        loaded_successfully = loaded_successfully + 1

    #Commit the transaction to the database
    print ("Committing ALL phase 2 changes...", end = "")
    transaction.commit()
    print ("Complete")

#endregion

#region Phase 3
# %%

if ExecutePhase3:

    #Now add participants to the participant tree structure if they are not already in it
    for _, p in root.participant_demographics_table.participants.iterrows():
        current_participant = next((x for x in root.participants if x.uid == p["UID"]), None)
        if (current_participant is None):
            current_participant = RePlayParticipant()
            current_participant.uid = p["UID"]
            root.participants.append(current_participant)

    #Commit the transaction to the database
    print ("Committing phase 3 changes...", end = "")
    transaction.commit()
    print ("Complete")

#endregion

#region Phase 4
# %%

if ExecutePhase4:

    #Now loop through the visits table and add visits to the tree structure as appropriate
    for _, v in root.visits_table.visits.iterrows():

        #Calculate the bounds of this visit
        try:
            (start_time, end_time) = VisitsTable.CalculateVisitBounds(v)
        except:
            #If we fail to calculate the bounds, then go on to the next visit
            continue

        #Grab the participant ID from this visit
        current_participant_uid = v["UID"]

        #Find this participant in the tree structure
        current_participant = None
        for p in root.participants:
            if p.uid == current_participant_uid:
                current_participant = p
                break

        #If the participant was found...
        if (current_participant is not None):
            #Check to see if this visit already exists for this participant
            existing_visit = None
            for cur_existing_visit in current_participant.visits:
                if ((cur_existing_visit.start_time == start_time) and (cur_existing_visit.end_time == end_time)):
                    existing_visit = cur_existing_visit
                    break
            
            #If not, then add it
            if (existing_visit is None):
                new_visit = RePlayVisit()
                new_visit.start_time = start_time
                new_visit.end_time = end_time
                new_visit.assignment_name = v["Prescription"]
                if (v["Setting"] == "Clinic"):
                    new_visit.is_at_home_visit = False
                else:
                    new_visit.is_at_home_visit = True

                current_participant.visits.append(new_visit)

    #Commit the transaction to the database
    print ("Committing phase 4 changes...", end = "")
    transaction.commit()
    print ("Complete")                

#endregion

#region Phase 5
# %%

if ExecutePhase5:

    #Now let's go through and find activities that need parent visits
    all_existing_uids = [x.uid for x in root.participants]
    for i in range(0, len(root.activity_list)):
        current_activity = root.activity_list[i]
        if (current_activity.parent_visit is None):
            activity_time = current_activity.start_time

            #Iterate over participants and visits
            for p in root.participants:
                for v in p.visits:
                    #If this activity falls within this visit for this participant, then maybe it belongs
                    #to this participant...
                    is_time_in_range = RePlayUtilities.time_in_range(v.start_time, v.end_time, activity_time)
                    if (is_time_in_range):
                        do_i_parent = True

                        if (current_activity.uid == p.uid):
                            #If the participant IDs match, then it definitely belongs
                            do_i_parent = True
                        elif (current_activity.uid in all_existing_uids):
                            #If the participant ID matches a DIFFERENT participant, then it does NOT belong
                            do_i_parent = False
                        else:
                            #Otherwise, assume it belongs
                            do_i_parent = True
                        
                        #Set the parent visit of this activity if the flag is true
                        if (do_i_parent):
                            current_activity.parent_visit = v
                            v.activities.append(current_activity)

    #Commit the transaction to the database
    print ("Committing phase 5 changes...", end = "")
    transaction.commit()
    print ("Complete")

#endregion

# %%

print ("DONE!")

#Close the connection to the database
db_connection.close()
# %%
