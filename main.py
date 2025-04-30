from fastapi import FastAPI, Request, Response, BackgroundTasks
from twilio.rest import Client
from pydantic import BaseModel
from message_processor import get_response_to_message
from chat_history_db import get_client_history, get_query_history

import os
import time

app = FastAPI()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(ACCOUNT_SID, AUTH_TOKEN)


def get_or_create_conversation(user_number: str) -> str:
    """
    Check if a conversation exists for this user; if not, create it.
    Uses the user's WhatsApp number as the friendly name.
    """
    # Check for existing conversation
    existing_convos = client.conversations.conversations.list(friendly_name=user_number)
    if existing_convos:
        return existing_convos[0].sid

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
        messaging_binding_proxy_address=f"whatsapp:{TWILIO_PHONE_NUMBER}"
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
        client.conversations.conversations(convo_sid).typing().create()

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

@app.post("/q")
def answer_question(item: Item):
    bot_response = get_response_to_message(item.message, "+12345678900")
    return {"received_message": f"OK.\n{bot_response}"}

@app.get("/client-history")
def client_history_endpoint():
    history = get_client_history()
    return {"client_history": history}

@app.get("/query-history")
def query_history_endpoint():
    history = get_query_history()
    return {"query_history": history}
