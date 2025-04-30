from fastapi import FastAPI, Request, Response, BackgroundTasks
from twilio.rest import Client
from pydantic import BaseModel
from message_processor import get_response_to_message
from chat_history_db import get_client_history, get_query_history

import os
import time
import requests
from requests.auth import HTTPBasicAuth

app = FastAPI()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_typing_indicator(conversation_sid: str):
    url = f"https://conversations.twilio.com/v1/Conversations/{conversation_sid}/Participants/{TWILIO_PHONE_NUMBER}/Typing"

    response = requests.post(
        url,
        auth=HTTPBasicAuth(ACCOUNT_SID, AUTH_TOKEN)
    )

    if response.status_code != 204:
        print(f"Failed to send typing indicator: {response.status_code} {response.text}", flush=True)

def get_or_create_conversation(user_number: str) -> str:
    """
    Checks for an existing conversation with friendly_name = user_number.
    Creates one if not found.
    """
    conversations = client.conversations.conversations.list(limit=50)  # page this if needed

    for convo in conversations:
        if convo.friendly_name == user_number:
            return convo.sid

    # Create a new conversation
    convo = client.conversations.conversations.create(friendly_name=user_number)
    return convo.sid



def add_participant_if_needed(conversation_sid: str, user_number: str):
    """
    Adds the WhatsApp user to the conversation if they're not already in it.
    """
    participants = client.conversations.conversations(conversation_sid).participants.list()
    for p in participants:
        if p.messaging_binding and p.messaging_binding.get("address") == user_number:
            return  # Already added

    # Add new participant
    client.conversations.conversations(conversation_sid).participants.create(
        messaging_binding_address=user_number,
        messaging_binding_proxy_address=TWILIO_PHONE_NUMBER
    )


def send_delayed_response(user_number: str, user_message: str):
    """
    Background task: send typing indicator and then the actual response.
    """
    try:
        # Get or create conversation
        convo_sid = get_or_create_conversation(user_number)

        # Ensure participant exists
        add_participant_if_needed(convo_sid, user_number)

        # Send typing indicator
        send_typing_indicator(convo_sid)

        # Get bot response
        response_text = get_response_to_message(user_message, user_number)

        # Send response
        client.conversations.conversations(convo_sid).messages.create(
            author=f"{TWILIO_PHONE_NUMBER}",
            body=response_text
        )

    except Exception as e:
        print(f"Error in conversation task: {e}", flush=True)

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    form_data = await request.form()
    incoming_message = form_data.get("Body", "").lower()
    sender_number = form_data.get("From", "")

    background_tasks.add_task(send_delayed_response, sender_number, incoming_message)

    return Response(status_code=200)


@app.get("/")
def read_root():
    return {"message": "Hello World"}

class Item(BaseModel):
    message: str
    number: str

@app.post("/q")
def answer_question(item: Item):
    bot_response = get_response_to_message(item.message, item.number)
    return {"received_message": f"OK.\n{bot_response}"}

@app.get("/client-history")
def client_history_endpoint(item: Item):
    history = get_client_history(item.number)
    return {"client_history": history}

@app.get("/query-history")
def query_history_endpoint(item: Item):
    history = get_query_history(item.message)
    return {"query_history": history}
