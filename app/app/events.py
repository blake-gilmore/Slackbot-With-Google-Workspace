from app import *
from flask import Response
from .bot_functions import validate_request, onboard, log_ts
import json
from googleapiclient.errors import HttpError

@slack_event_adapter.on('reaction_added')
@validate_request
def reaction(payload):
    event = payload.get('event', {}) #look for 'key' event in payload, if its not there return a blank dictionary {}
    user_id = event.get('user')
    convo = client.conversations_open(users= user_id)
    channel_id = convo['channel']['id'] #payload gives the item that the reaction was added to and you get the channel of that item

    if channel_id not in welcome_messages or f'@{user_id}' not in welcome_messages[channel_id]:
        return Response(), 200

    welcome = welcome_messages[channel_id][f'@{user_id}']
    welcome.completed = True #once the reaction was added then the welcome is complete
    welcome.channel = channel_id
    message = welcome.get_message()
    updated_message = client.chat_update(**message)
    welcome.timestamp = updated_message['ts']

    return Response(), 200

@slack_event_adapter.on('message')
@validate_request
def message(payload):
    try:
        event = payload.get('event', {}) #look for 'key' event in payload, if its not there return a blank dictionary {}
        message_ts = event.get('ts')

        #This message is valid. We should mark it in our validated timestamps and increase the index
        if not log_ts(message_ts):
            return Response(), 400

        user_id = event.get('user') #getting these from the event key
        text = event.get('text')
        channel_id = event.get('channel')
        thread_ts = event.get('thread_ts', {})

        if BOT_ID == user_id:
            print("Bot sent this message. Not validating it.")
            return Response(), 400

        if event.get('channel_type') != 'im':
            return Response(), 400

        ########
        # Confirmed a DM, now check if it's in a thread
        if thread_ts == {}:
            return Response(), 400

        ########
        # Confirmed in a thread, now retrieve the replies using conversations.replies
        replies = client.conversations_replies(channel=channel_id, ts=thread_ts)
        parent_message  = (replies.get('messages'))[0]

        #get timesstamp to check if it's an onboard_message that's being responded to
        parent_ts = parent_message['ts']

        #Open JSon to check if the timestamp is the same
        with open(parentFolder + "/data/onboard_timestamp.json", "r") as file:
                json_data = json.load(file)

        #Compare the timestamps
        if parent_ts != json_data['onboard_timestamp']:
            print("Not an onboard message being responded to")
            return Response(), 400

        trigger_id = json_data['trigger_id']

        #We now know that this is a validated onboard message
        #Check that this message has a file and that it's of the correct type
        files = event.get("files", {})
        if files == {} or (len(files) != 1) or (files[0].get('filetype') != 'csv'):
            #Error in files attachment
            print("Files wrong, bye bye")
            return Response(), 400

        #This message is valid. We should mark it in our validated timestamps and increase the index
        with open(parentFolder + "/data/validated_timestamps.json", "r") as file:
            json_data = json.load(file)



        #Pass it over to a function that will do work for the onboard message function
        onboard(event, trigger_id)

    except HttpError as error:
        print(error)
    

    return Response(), 200


