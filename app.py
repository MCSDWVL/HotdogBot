import os
import logging
from flask import Flask
from slack_sdk.web import WebClient
from slackeventsapi import SlackEventAdapter
from bot_test_messages import BotTestMessages
import bot_bank_functions as BotBank
import setupdatabase as DatabaseHelper


# Initialize a Flask app to host the events adapter
app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(os.environ['SLACK_SIGNING_SECRET'], "/slack/events", app)

# Initialize a Web API client
slack_web_client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])

# Track messages we've handled to try to not double handle them.
handled_message_ids = set()


# help command.
def identify_yourself(user_id: str, channel: str):
    # Post the help message in Slack
    response = slack_web_client.chat_postMessage(
        channel=channel, 
        text="""I'm an ordinary, dirty trash robot :robot_face: with a brain :brain: full of hot dogs :hotdog: and a body that says \"my body is full of hot dogs :hotdog: :hotdog: :hotdog:, please help.\"\n\n
        You can use the following commands:\n
         `@HotdogBot pay @someone 10` send money to someone\n
         `@HotdogBot balance` check your balance\n
         `@HotdogBot reset` reset every user to $100\n
         `@HotdogBot inflation` give everyone money\n
         `@HotdogBot ante` add yourself if you don't exist yet
         `@HotdogBot create @username` add a user that doesn't exist yet
        """
    )


# creating a new account
def add_new_user(user_id: str, channel: str):
    balance = BotBank.new_user(user_id)
    response = slack_web_client.chat_postMessage(
        channel=channel, 
        text=f"{user_id} has {balance} points"
    )


# Debug respond to an event so you can see what is happening directly in slack.
def debug_event(channel: str, payload):
    event = payload.get("event", {})
    user = event.get("user", {})
    type = event.get("type", {})
    timestamp = event.get("event_ts", {})
    response = slack_web_client.chat_postMessage(
        channel=channel, 
        #text=f"user: {user} type: {type}"
        text=f"full event:\n {event}"
    )


# ================ Team Join Event =============== #
# When the user first joins a team, the type of the event will be 'team_join'.
@slack_events_adapter.on("team_join")
def add_user(payload):
    # not implemented, debug event
    event = payload.get("event", {})
    print(event)


# ============= Reaction Added Events ============= #
# When a users adds an emoji reaction, the type of the event will be 'reaction_added'.
@slack_events_adapter.on("reaction_added")
def update_emoji(payload):
    # not implemented, leaving as an example if I want to handle reactions
    event = payload.get("event", {})
    print(event)


# =============== Pin Added Events ================ #
# When a users pins a message the type of the event will be 'pin_added'.
# Here we'll link the update_pin callback to the 'reaction_added' event.
@slack_events_adapter.on("pin_added")
def update_pin(payload):
    # not implemented, leaving as an example if I want to handle pins
    event = payload.get("event", {})
    print(event)


# ============== Message Events ============= #
# When a user sends a DM, the event type will be 'message'.
# Here we'll link the message callback to the 'message' event.
@slack_events_adapter.on("message")
def message(payload):
    # not implemented, leaving as an example if I want to handle dms
    event = payload.get("event", {})
    print(event)


# check if user is an admin of the workspace for access controlled commands.
def is_admin(user_id):
    return slack_web_client.users_info(user=user_id).get("user").get("is_admin")


# ============== Mention Events ============= #
# here's the giant function of everything that happens when you @Bot
@slack_events_adapter.on("app_mention")
def handle_message(payload):
    event = payload.get("event", {})
    msg_id = event.get("client_msg_id")
    channel_id = event.get("channel")

    if msg_id in handled_message_ids:
        print("skipping duplicate event")
        print(event)
        return
    handled_message_ids.add(msg_id)
    print(event)
    print(handled_message_ids)

    user_id = event.get("user")
    text = event.get("text")
    bot_id = event.get("bot_id")
    if bot_id is not None:
        print("I don't respond to bots")
        return

    debug_all = False
    if debug_all:
        debug_event(channel_id, payload)

    # split text into pieces
    pieces = text.split()
    
    print(f"pieces: {pieces}")

    # say hello
    if len(pieces) == 1:
        identify_yourself(user_id, channel_id)
        return

    # paying
    if 'pay' == pieces[1].lower():
        recipient_id = event.get("blocks")[0].get("elements")[0].get("elements")[2].get("user_id")
        recipient_name = pieces[2]
        amount = pieces[3]
        payer_name = slack_web_client.users_info(user=user_id).get("user").get("name")
        result = BotBank.pay(user_id, recipient_id, int(amount))
        if result is None:
            response = slack_web_client.chat_postMessage(
                channel=channel_id, 
                text=f"Payment failed."
            )
        else:
            response = slack_web_client.chat_postMessage(
                channel=channel_id, 
                text=f"@{payer_name} ({result[0]}) pays {amount} to {recipient_name} ({result[1]})"
            )
        return
    
    # check balance
    if 'balance' == pieces[1].lower():
        result = BotBank.get_balance(user_id)
        if result is None:
            response = slack_web_client.chat_postMessage(
                channel=channel_id, 
                text=f"Something went wrong."
            )
            return
        else:
            response = slack_web_client.chat_postMessage(
                channel=channel_id, 
                text=f"Your balance is: {result}"
            )
            return

    # manually add user
    if 'create' == pieces[1].lower():
        recipient_id = event.get("blocks")[0].get("elements")[0].get("elements")[2].get("user_id")
        recipient_name = pieces[2]
        result = BotBank.BotBank.new_user(recipient_id)
        if result is None:
            response = slack_web_client.chat_postMessage(
                channel=channel_id, 
                text=f"User already exists."
            )
        else:
            response = slack_web_client.chat_postMessage(
                channel=channel_id, 
                text=f"@{recipient_id} added with ${result}"
            )
        return   
    
    # manually add self
    if "ante" in text:
        result = BotBank.new_user(user_id)
        if result is None:
            response = slack_web_client.chat_postMessage(
                channel=channel_id, 
                text=f"User already exists."
            )
        else:
            response = slack_web_client.chat_postMessage(
                channel=channel_id, 
                text=f"@{user_id} added with ${result}"
            )
        return
    
    # inflation
    if "inflation" == pieces[1].lower():
        # check that being requested by admin.
        allowed = is_admin(user_id)
        if not allowed:
            response = slack_web_client.chat_postMessage(
               channel=channel_id, 
                text="Forbidden."
            )
            return
        
        # give all users some money
        users_list = slack_web_client.users_list()
        for user in users_list.get("members"):
            id = user.get("id")
            name = user.get("name")
            new_balance = BotBank.update_balance(id,  BotBank.get_balance(id) + 10)
            response = slack_web_client.chat_postMessage(
                channel=channel_id, 
                text=f"Adding 10 to {name}: {new_balance}"
            )
        return
    
    # reset
    if "reset" == pieces[1].lower():
        # check that being requested by admin.
        allowed = is_admin(user_id)
        if not allowed:
            response = slack_web_client.chat_postMessage(
               channel=channel_id, 
                text="Forbidden."
            )
            return
        
        # recreate the tables.
        DatabaseHelper.create_tables()

        # add all users with starter money.
        users_list = slack_web_client.users_list()
        for user in users_list.get("members"):
            newbalance = BotBank.new_user(user.get("id"))
            user_name = user.get("name")
            response = slack_web_client.chat_postMessage(
                channel=channel_id, 
                text=f"Adding {user_name} with ${newbalance}"
            )
        return


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    app.run(port=3000)
