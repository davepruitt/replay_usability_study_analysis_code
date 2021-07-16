import pandas
import pickle
import os
import pathlib
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

class GoogleSheets:

    #Static variables

    PATH_TO_CREDENTIALS = os.path.join(os.getcwd(), "Assets", "Replay-5b4318531d17.json") #The credentials file has been removed for the Github release
    SCOPES = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/spreadsheets.readonly"]
    Service = None

    #Static methods

    #This method initializes the Google service and MUST be called before the application 
    #is able to read or write any data to Google Sheets or Google Drive
    @staticmethod
    def InitializeGoogleSheets ():
        
        creds = service_account.Credentials.from_service_account_file(GoogleSheets.PATH_TO_CREDENTIALS, scopes = GoogleSheets.SCOPES)
        GoogleSheets.Service = build('sheets', 'v4', credentials=creds)
    
    #This method requests a specific spreadsheet from Google, given the "sheet id" and the name
    #of the tab within that spreadsheet.
    @staticmethod
    def ReadSpreadsheetWithID (spreadsheet_id, tab_name):
        values = None
        if GoogleSheets.Service is not None:
            result = GoogleSheets.Service.spreadsheets().values().get(spreadsheetId = spreadsheet_id, range = tab_name).execute()
            values = result.get("values", [])
        return values

    #This method requests a specific spreadsheet from Google, given the "sheet id" and the name
    #of the tab within that spreadsheet. It returns a Pandas dataframe rather than a normal Python list.
    @staticmethod
    def ReadSpreadsheetWithID_ReturnPandasDataFrame (spreadsheet_id, tab_name, replace_column_headers = True):
        result = GoogleSheets.ReadSpreadsheetWithID(spreadsheet_id, tab_name)
        pandas_result = pandas.DataFrame(data = result)

        #Replace the default column headers created by pandas
        #with the first row from the spreadsheet, which are 
        #the actual column headers that are in the spreadsheet
        if replace_column_headers:
            new_column_headers = pandas_result.iloc[0]
            pandas_result = pandas_result[1:]
            pandas_result.columns = new_column_headers

        #Now return the dataframe to the caller
        return pandas_result

    #This method reads a published (public) spreadsheet found at any URI/URL/path.
    #This method does NOT require you to call the "InitializeGoogleSheets" method beforehand,
    #but it DOES require the spreadsheet to be in a publicly accessible location.
    @staticmethod
    def ReadPublicSpreadsheetFromURL (url):
        data = pandas.read_csv(url, sep='\t')
        return data