from __future__ import print_function

import os.path
import pandas as pd
import numpy as np

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

#["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
#"https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

# The ID and range of a sample spreadsheet.
SAMPLE_RANGE_NAME = 'A:Z'

# Documentation and API reference 
# https://googleapis.github.io/google-api-python-client/docs/dyn/sheets_v4.spreadsheets.html
# API reference https://developers.google.com/sheets/api/reference/rest

def get_authenticated_sheets_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('sheets', 'v4', credentials=creds)
        print("Authenticated into google sheets")
        return service
    
    except HttpError as err:    
        print(err)
        return


class Sheets:
    '''Google sheets service helper class'''
    def __init__(self, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
        self.service = get_authenticated_sheets_service()

    def get_df_from_sheet(self, sheet_name):
        '''Converts the google sheet to a pandas df.'''
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id, range=SAMPLE_RANGE_NAME).execute()
            
        rows = result.get('values', [])
        print(f"{len(rows)} rows retrieved")
        df = pd.DataFrame(rows, columns = rows[0])
        df = df.iloc[1:]
        # Replace all None and "" values with NaN
        df = df.fillna(value=np.nan)
        df = df.replace(r'^\s*$', np.nan, regex=True)
        
        return df

    def update_sheet_from_df(self,  df, sheet_name):
        '''Updates the google sheet given the pandas df'''
        d = df.fillna("")
        
        # Write the DataFrame to the sheet
        values =  [list(d.columns)] + d.values.tolist()
        values = [[str(v) for v in row] for row in values]
        
        body = {
            'values': values
        }

        result = self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id, range="fact_videos",
            valueInputOption='USER_ENTERED',#'RAW',
            body=body).execute()
        print(f'{result["updatedCells"]} cells updated.')