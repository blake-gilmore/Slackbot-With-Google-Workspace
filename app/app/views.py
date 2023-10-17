from app import app, client, service, parentFolder
from flask import Response, request
from .bot_functions import validate_request, create_accounts_from_form, log_trigger_id
import json, pprint
from datetime import datetime


#Route used for triggers coming from the /onboard-interns command
@app.route('/request-url', methods=['POST'])
@validate_request
def request_url():
    data = json.loads(request.form['payload'])
    actionsList = data.get('actions', {})

    if actionsList == {}:
        #actions for adding google workspace members
        create_accounts_from_form(data)
        return Response(), 200
    
    action_id = actionsList[0]['action_id']
    trigger_id = data['trigger_id']


    #Check if this is a repeated request from the Slack server
    if not log_trigger_id(trigger_id):
        print("Already processed this.")
        return Response(), 200

    if action_id == 'onboard_interns':
        local_filepath = parentFolder + "/data/onboard_message.json"
        with open(local_filepath, "r") as file:
            onboard_message = json.load(file)
            onboard_message['trigger_id'] = trigger_id

        client.views_open(**onboard_message)

        return Response(), 200

    return Response(), 200 #return empty response and status code 200 which means okay

def build_users():
    #Builds a list of users
    #List of dictionaries with each user where
    #User dictionary has
    #     Full name, workspace email, MFA authorized, lastLogin
    users = service.users().list(customer="my_customer").execute()
    built_list = []
    
    #Next, iterate through user list and for every one add to the list a dictionary
    for user in users['users']:
        next_user = {
            "MFA": user['isEnrolledIn2Sv'],
            "lastLogin": user['lastLoginTime'],
            "creationTime": user['creationTime'],
            "email": user['primaryEmail'],
            "name": user['name']['fullName'],
        }
        built_list.append(next_user) 
        
    return built_list

def output_check(built_list):
    #Prints an output of users that aren't enrolled in MFA
    #Prints an output of users that haven't logged into Google for 90 days
    noMFA_list = [user for user in built_list if user['MFA'] == False]
    inactive_list = [user for user in built_list if 
        (datetime.now() - datetime.strptime(user['lastLogin'], "%Y-%m-%dT%H:%M:%S.000Z")).days >= 90 
        and 
        (datetime.now() - datetime.strptime(user['creationTime'], "%Y-%m-%dT%H:%M:%S.000Z")).days >= 90
    ]
    print("List of users with no MFA activated:")
    pprint.pprint(noMFA_list)
    print("\nList of users inactive for 90 days:")
    pprint.pprint(inactive_list)


@app.route('/list-admins', methods=['POST'])
@validate_request
def list_admins():
    built_list = build_users()
    output_check(built_list)
    return Response(), 200   

@app.route('/onboard-interns', methods=['POST'])
@validate_request   
def onboard_interns():

    # try:
    data = request.form
    user_id = data.getlist('user_id')[0]

    # Call the users.info API method to retrieve user information
    user_info = client.users_info(user=user_id)
    
    # Extract the user's email
    user_email = user_info['user']['profile']['email']

    #Check if person sending request is an admin
    users = service.users().list(customer='my_customer', query="isAdmin=true").execute()

    # Extract the user data
    user_list = users.get('users', [])

    trigger_id = data.get('trigger_id')
    print("trigger_id: " + trigger_id)

    email_list = []
    for user in user_list:
        email_list.append(user['primaryEmail'])

    if user_email not in email_list:
        #
        #
        #Need to add a message saying only available with admin email account
        #
        #
        print("Not admin")
        return Response(), 400

    #User is admin. Send a message requesting an excel sheet
    #Start by getting the correct channel with the correct user
    response = client.conversations_open(users=user_id)
    pprint.pprint(response)
    channel_id = response['channel']['id']
    print(channel_id)

    #Build message and send
    # Send the initial message
    response = client.chat_postMessage(
        channel=channel_id,
        text="To onboard new interns, please respond to this message in a thread and upload a .csv file with the new intern's information. \n\nRefer to the example file attached in the thread."
    )
    # # Get the timestamp of the initial message to use as the thread_ts
    # Read the JSON data from the file
    with open(parentFolder + "/data/onboard_timestamp.json", "r") as file:
        json_data = json.load(file)

    # Get the thread_ts value from the response (I assume it's a valid value)
    thread_ts = response["ts"]

    # Update the "onboard_timestamp" field with the new value
    json_data["onboard_timestamp"] = thread_ts
    json_data["trigger_id"] = trigger_id

    # Write the updated JSON data back to the file
    with open(parentFolder + "/data/onboard_timestamp.json", "w") as file:
        json.dump(json_data, file)
    
    return Response(), 200