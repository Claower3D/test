import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

spreadsheet_id = "1n7Y33bjw6LH4kCd53_1kzbPfftqL3pfOS_pNtyWf3t4" # user's spreadsheet from before
try:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    print("Metadata fetched successfully!")
except Exception as e:
    import traceback
    traceback.print_exc()
