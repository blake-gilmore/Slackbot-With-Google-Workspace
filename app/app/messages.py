from app import service
import json

class simpleResponse:
    def __init__(self, textToSend, channel, user):
        self.text = {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': (
                    f'\n\n{textToSend}\n\n'
                )
            }
        }
        self.timestamp = ''
        self.channel = channel
        self.user = user
    
    def get_message(self):
        return {
            'ts': self.timestamp,
            'channel': self.channel,
            'blocks': [
                self.text
            ]
        }

#basic format of the Welcome Message that's
class WelcomeMessage:
    START_TEXT = {
        'type': 'section',
        'text': {
            'type': 'mrkdwn',
            'text': (
                'Welcome to this awesome channel! \n\n'
                '*Get started by completing the tasks!*'
            )
        }
    }

    DIVIDER = {'type': 'divider'}

    def __init__(self, channel, user):
        self.channel = channel
        self.user = user
        self.icon_emoji = ':robot_face:' #colons surrounding word denote emoji - lets us add an emoji besides the bot
        self.timestamp = '' # want to know what time the message was sent at
        self.completed = False #keeps track of task completion

    def get_message(self):
        return {
            'ts': self.timestamp,
            'channel': self.channel,
            'username': 'Welcome Robot!',
            'icon_emoji': self.icon_emoji,
            'blocks': [
                self.START_TEXT,
                self.DIVIDER,
                self._get_reaction_task()
            ]
        }

    def _get_reaction_task(self): #underscore means private method that shouldn't be called outside class
        checkmark = ':white_check_mark:'
        if not self.completed:
            checkmark = ':white_large_square:'
        
        text = f'{checkmark} *React to this message!*'

        return {'type': 'section', 'text': {'type': 'mrkdwn', 'text': text}}


def onboard_message_generator(interns, trigger):
    #Build the list of options for each user
    #Consists of every group minus the Group
    groups = [(group['name']) for group in (service.groups().list(customer='my_customer').execute())['groups']]

    with open('/config/hidden_data.json', 'r') as json_file:
        # Parse the JSON data from the file
        data = json.load(json_file)
        
    for group in data['groups_to_remove']:
        groups.remove(group)

    options = []

    for group in groups:
        options.append({
            "value": group,
            "text": {
                "type": "plain_text",
                "text": group
            }
        })

    #Build the blocks for the message
    blocks = []
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "Please review the following intern accounts that will be created. If any of the information is not correct, please select 'Close' and verify the information in the .csv spreadsheet you uploaded is correct." + "\n---\n"
        }
    })
    
    for intern in interns:
        intern_first_name, intern_last_name = intern.split()
        intern_email = interns[intern]
        intern_primary_email = intern_first_name.lower()+'.'+intern_last_name.lower()+'@' + data['domain_name']

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "---\n" + 
                            intern + "\n" +
                            "Email: " + intern_primary_email + "\n" 
                            "Secondary Email: " + intern_email + "\n"
                },
                "accessory": {
                    "type": "checkboxes",
                    "action_id": intern,
                    "options": options
                }
            }
        )
        # pprint.pprint(blocks)


    full_message = {
        "trigger_id": trigger,
        "view": {
            "type": "modal",
            "title": {
                "type": "plain_text",
                "text": "Intern Onboarding"
            },
            "submit": {
                "type": "plain_text",
                "text": "Submit"
            },
            "close": {
                "type": "plain_text",
                "text": "Cancel"
            }, 
            "blocks": blocks
        }
    }



    return full_message

def new_member_form(channel_id):
#returns a slack block-message form for a user first and last name input
#takes in the channel id the message will be sent to
    return {
        "channel": channel_id,
        "blocks": [
            {
                "block_id": "Question",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Please fill out the form below:"
                }
            },
            {
                "block_id": "first_name_input",
                "type": "input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "first_name"
                },
                "label": {
                    "type": "plain_text",
                    "text": "First Name"
                }
            },
            {
                "block_id": "last_name_input",
                "type": "input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "last_name"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Last Name"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Submit"
                        },
                        "style": "primary",
                        "action_id": "new_member_form"
                    }
                ]
            }
        ]
    }
