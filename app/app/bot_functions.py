import hmac, hashlib, time, requests, csv, pprint, base64, pprint, json
from config.get_Email_Message import get_Email_Message
from app import *
from flask import request, Response
from .messages import WelcomeMessage, onboard_message_generator
from functools import wraps
from googleapiclient.errors import HttpError
from password_generator import PasswordGenerator
from app import parentFolder
from googleapiclient.http import MediaFileUpload
from openpyxl import load_workbook

def send_welcome_message(channel, user):
    if channel not in welcome_messages:
        welcome_messages[channel] = {}

    if user in welcome_messages[channel]:
        return

    welcome = WelcomeMessage(channel, user)
    message = welcome.get_message()
    response = client.chat_postMessage(**message) #** is the unpack operator and sets up all the keyword values in the function like ts=the timestamp and channel=the channel
    welcome.timestamp = response['ts']
    welcome_messages[channel][user] = welcome

#Validates request by checking hash against signing secret
def validate_request(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        #Set variables for all types of requets
        version_number = "v0"
        
        try:
            #Check for POST request
            if True or request.method == "POST" and request.path == "/request-url":

                #Collect strings and concatenate for validation
                version_number = "v0"
                request_body = (request.get_data()).decode('utf8', 'strict')
                timestamp = (request.headers).get("X-Slack-Request-Timestamp")
                request_tuple = (version_number, timestamp, request_body)
                validate_string = ":".join(request_tuple)

                #Check for possible replay attack
                if abs(time.time() - float(timestamp)) > 60 * 5:
                    # The request timestamp is more than five minutes from local time.
                    # It could be a replay attack, so let's ignore it.
                    return Response(), 400

                
                #Compute hex digest and compare to Slack Signature
                slack_signature = (request.headers).get("X-Slack_Signature")

                my_signature = 'v0=' + (hmac.new(global_signing_secret.encode(), validate_string.encode(), hashlib.sha256).hexdigest())
                
                if slack_signature == my_signature:
                    # hooray, the request came from Slack!
                    print("Request Validated\n")

                else:
                    return Response(), 400

            elif request.method == "GET":
                return Response(), 400
        
        except:
            return Response(), 400

        return func(*args, **kwargs)
        
    return decorated_function


###########################################################

def log_trigger_id(trigger_id):
    with open(parentFolder + "/data/trigger_id_list.json", "r") as file:
            json_data = json.load(file)

    if trigger_id in json_data['validated_messages']['message_array']:
        print("This message has been looked at.")
        return False
    else:
        currentIndex = json_data['validated_messages']['current_index']
        if currentIndex == json_data['max_messages']:
            currentIndex = 0
        json_data['validated_messages']['message_array'][currentIndex] = trigger_id
        nextIndex = currentIndex + 1
        if (currentIndex == json_data['max_messages']):
            nextIndex = 0
            
        json_data['validated_messages']['current_index'] = nextIndex;

        with open(parentFolder + "/data/trigger_id_list.json", "w") as file:
            json.dump(json_data, file)
        return True


###########################################################


#Intended to check if a message is being double sent. We don't want to process the same message twice
def log_ts(timestamp):
    with open(parentFolder + "/data/validated_timestamps.json", "r") as file:
            json_data = json.load(file)

    if timestamp in json_data['validated_messages']['message_array']:
        print("This message has been looked at.")
        return False
    else:
        currentIndex = json_data['validated_messages']['current_index']
        if currentIndex == json_data['max_messages']:
            currentIndex = 0
        json_data['validated_messages']['message_array'][currentIndex] = timestamp
        nextIndex = currentIndex + 1
        if (currentIndex == json_data['max_messages']):
            nextIndex = 0
            
        json_data['validated_messages']['current_index'] = nextIndex;

        with open(parentFolder + "/data/validated_timestamps.json", "w") as file:
            json.dump(json_data, file)
        return True



############################################################################




def email_new_user(primary_email, secondary_email, password, first_name):
    try:
        message = get_Email_Message(primary_email, secondary_email, password, first_name)
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {
            'raw': encoded_message
        }
        #############################
        send_message = (gmail_service.users().messages().send
                        (userId='me', body=create_message).execute())
        #############################
        print(f"Sending a message to email: {secondary_email} ")

    except HttpError as error:
        print(error)
    
    return


###################################################################


def create_account(first_name, last_name, secondary_email, groups):
    try:
        with open('/config/hidden_data.json', 'r') as json_file:
            # Parse the JSON data from the file
            data = json.load(json_file)
        domain_name = data['domain_name']
        intern_primary_email = first_name.lower()+'.'+ last_name.lower()+ domain_name

        pwo = PasswordGenerator()
        pwo.minlen = 12
        pwo.maxlen = 12

        intern_password = pwo.generate()

        user = {
            'name': {
                'givenName': first_name,
                'familyName': last_name
            },
            'primaryEmail': intern_primary_email,
            'recoveryEmail': secondary_email,
            'password': intern_password,
            'changePasswordAtNextLogin': True
        }

        #############################
        created_user = service.users().insert(body=user).execute()
        #############################

        print("---------------------------------------------\nCreating User: ")
        print(user)        

        member = {"email":intern_primary_email, "role": "MEMBER"}

        group_dict = {}

        all_groups = (service.groups().list(customer='my_customer').execute())['groups']

        for group in all_groups:
            if group['name'] in groups:
                group_dict[group['name']] = group['email']

        print("----------------------------------\nGroups to be added to:")
        pprint.pprint(group_dict)


        for group in group_dict:
            #############################
            service.members().insert(groupKey=group_dict[group], body=member).execute()
            #############################
            print(f"Inserting: GroupKey = {group_dict[group]}, body= {member}")

        email_new_user(intern_primary_email, secondary_email, intern_password, first_name)
        

    except HttpError as error:
        print(error)

    return


##################################################################

def create_accounts_from_form(data):
    try:
        #Make dictionary from data sent in of all intern options
        values_dict = data['view']['state']['values']
        groups_dict = {}

        for block in values_dict:
            groups_dict[next(iter(values_dict[block]))] = values_dict[block][next(iter(values_dict[block]))]['selected_options']

        local_filepath = parentFolder + "/data/interns.json"
        with open(local_filepath, "r") as file:
            interns = json.load(file)

        #Loops through each intern in the list
        for intern in interns:
            #Get the first and last name from the intern object
            intern_first_name, intern_last_name = intern.split()

            #Get the email from the intern object
            intern_email = interns[intern]
        
            #create list of groups
            with open('/config/hidden_data.json', 'r') as json_file:
                # Parse the JSON data from the file
                data = json.load(json_file)
            groups = []
            groups.append(data['team_string'])
            groups.append('Interns')

            for group in groups_dict[intern]:
                groups.append(group['value'])

            #create the account with a function call
            create_account(intern_first_name, intern_last_name, intern_email, groups)
            create_intern_folder(intern_first_name, intern_last_name)

        print("Success!")
    except HttpError as error:
        print(error)

    return Response(), 200



#######################################################################

def create_intern_folder(intern_first_name, intern_last_name):
    with open('/config/noreply_email.json', 'r') as json_file:
        # Parse the JSON data from the file
        data = json.load(json_file)
    parent_folder_id = data['parent_folder_id']
    with open('/config/hidden_data.json', 'r') as json_file:
        # Parse the JSON data from the file
        data = json.load(json_file)
    intern_string = "interns@" + data['domain_name']
    lead_string = "leads@" + data['domain_name']
    try:
        permissions = [
            {
                'type': 'group',
                'role': 'writer',
                'emailAddress': intern_string
            },
            {
                'type': 'group',
                'role': 'fileOrganizer',
                'emailAddress': lead_string
            }
        ]

        folder_metadata = {
            'name': " ".join([intern_first_name, intern_last_name]),
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }

        folder = drive_service.files().create(body=folder_metadata, supportsAllDrives=True, fields='id').execute()
        print(f'Created folder: "Interns" (ID: {folder["id"]})')

        try:
            intern_folder_id = folder["id"]

            wb = load_workbook(parentFolder + "/data/Intern_Timesheet.xlsx")
            sheet = wb['TIMESHEET TEMPLATE']
            sheet['B3'] = " ".join([intern_first_name, intern_last_name])
            wb.save(parentFolder + "/data/Updated_Intern_Timesheet.xlsx")

        except Exception as e:
            print(f"An error occurred: {e}")

        try:
            file_metadata = {
                'name': " ".join([intern_first_name, intern_last_name]) + " Timesheet",
                'mimeType': 'application/vnd.google-apps.spreadsheet',
                'parents': [intern_folder_id]
            }
            media = MediaFileUpload(parentFolder + "/data/Updated_Intern_Timesheet.xlsx",
                                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
            
            file = drive_service.files().create(body=file_metadata, supportsAllDrives=True, media_body=media,
                                        fields='id').execute()
        except Exception as e:
            print(f"An error occurred: {e}")
                                      
        print(F'File ID: "{file.get("id")}".')
        return file.get('id')

    except HttpError as error:
        print(error)




def onboard(body_event, trigger_id):
    try:
        url_private_download = body_event['files'][0]['url_private_download']
        headers = {
            "Authorization": f"Bearer {os.environ['SLACK_TOKEN']}"
        }
        response = requests.get(url_private_download, headers=headers)

        # You can find the file at slack-api-client/target/sample.txt
        local_filepath = parentFolder + "/uploads/interns.csv"
        with open(local_filepath, "wb") as file:
            file.write(response.content)

        with open(local_filepath, "r") as file:
            body = file.read().replace('\n', '')

        #Check that the file given has name and email columns
        required_columns = ['Name', 'Email']
        headers_found = True

        with open(local_filepath, "r", newline="") as file:
            # Read the CSV file without assuming the presence of a header row
            lines = list(csv.reader(file))
            header_row = -1

        header_indices = {}
        
        # Get the header row (if available)
        for i in range(len(lines)):
            headers = lines[i] if lines else []
            headers_found = all(column in headers for column in required_columns)
            if headers_found:
                header_indices["Name"] = headers.index("Name")
                header_indices["Email"] = headers.index("Email")
                header_row = i
                break

        #CSV has been looped through, check if a header row with both has been found
        if header_row == -1:
            print("No Headers")
            return Response(), 400

        #Create dictionary of all interns
        name_selection = (lines[header_row+1][header_indices['Name']]).strip()
        email_selection = lines[header_row+1][header_indices["Email"]]

        interns = {}
        
        currentRow = header_row+1

        while (currentRow < len(lines)) and name_selection != "" and email_selection != "":
            interns[name_selection] = email_selection
            name_selection = (lines[currentRow][header_indices["Name"]]).strip()
            email_selection = lines[currentRow][header_indices["Email"]]
            currentRow = currentRow + 1

        if name_selection != "" and email_selection != "":
            interns[name_selection] = email_selection

        users = service.users().list(customer='my_customer').execute()
        
        for user in users['users']:
            if f"{user['name']['givenName']} {user['name']['familyName']}" in interns:
                del interns[f"{user['name']['givenName']} {user['name']['familyName']}"]

        if interns == {}:
            print("No new interns!")
            return Response(), 200

        print(interns)

        onboard_message = onboard_message_generator(interns, trigger_id)

        local_filepath = parentFolder + "/data/onboard_message.json"
        with open(local_filepath, "w") as file:
            json.dump(onboard_message, file)

        local_filepath = parentFolder + "/data/interns.json"
        with open(local_filepath, "w") as file:
            json.dump(interns, file)

        channel_id = body_event.get('channel')
        print("Channel_id: " + channel_id)

        onboard_prompt = {
            "channel": channel_id,
            "blocks": [
                {
                    "block_id": "Question",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Please press the button below when ready to verify new intern information."
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Ready"
                            },
                            "style": "primary",
                            "action_id": "onboard_interns"
                        }
                    ]
                }
            ]
        }
        client.chat_postMessage(**onboard_prompt)

    except HttpError as error:
        print(error)

    return Response(), 200