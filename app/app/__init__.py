from __future__ import print_function

import slack_sdk, os, json
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from slackeventsapi import SlackEventAdapter

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2 import service_account

parentFolder = os.path.dirname(os.path.abspath(__file__))
env_path = Path(parentFolder + '/config/.env')
load_dotenv(dotenv_path=env_path)
app = Flask(__name__) #configure Flask application
app.config.from_object('config')
global_signing_secret = os.environ['SIGNING_SECRET']
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'],'/slack/events', app)

client = slack_sdk.WebClient(token=os.environ['SLACK_TOKEN']) #specific client from slack
BOT_ID = client.api_call("auth.test")['user_id']#returns id of bot

admin_creds = None
gmail_creds = None

message_counts = {}
welcome_messages = {}

#Google set up
ADMIN_SCOPES = ['https://www.googleapis.com/auth/admin.directory.user', 'https://www.googleapis.com/auth/admin.directory.group']
GMAIL_SCOPES =  ['https://mail.google.com/']
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']

if os.path.exists(parentFolder + '/config/admin_token.json'):
    admin_creds = Credentials.from_authorized_user_file(parentFolder + '/config/admin_token.json', ADMIN_SCOPES)

# If there are no (valid) credentials available, let the user log in.
if not admin_creds or not admin_creds.valid:
    if admin_creds and admin_creds.expired and admin_creds.refresh_token:
        admin_creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            parentFolder + '/config/credentials.json', ADMIN_SCOPES)
        admin_creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open(parentFolder + '/config/admin_token.json', 'w') as token:
        token.write(admin_creds.to_json())

gmail_creds = service_account.Credentials.from_service_account_file(parentFolder + '/config/service-key.json', scopes=GMAIL_SCOPES)
service_creds = service_account.Credentials.from_service_account_file(parentFolder + '/config/service-key.json', scopes=DRIVE_SCOPES)

with open('/config/noreply_email.json', 'r') as json_file:
    # Parse the JSON data from the file
    data = json.load(json_file)

noreply_credentials = gmail_creds.with_subject(data['email'])

service = build('admin', 'directory_v1', credentials=admin_creds)
gmail_service = build('gmail', 'v1', credentials=noreply_credentials)
drive_service = build('drive','v3', credentials=service_creds)

from app import views
from app import events
    