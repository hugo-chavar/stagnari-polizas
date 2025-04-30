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
CONVERSATION_SID = os.getenv("TWILIO_CONVERSATION_SID")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_delayed_response(to_number: str, user_message: str):
    """
    Send typing indicator and then the full response via Twilio Conversations API.
    """

    # Ensure participant exists in the conversation
    try:
        client.conversations \
            .conversations(CONVERSATION_SID) \
            .participants \
            .create(messaging_binding_address=to_number,
                    messaging_binding_proxy_address=f"whatsapp:{TWILIO_PHONE_NUMBER}")
    except Exception as e:
        if "Participant already exists" not in str(e):
            print(f"Error adding participant: {e}")
            return

    # Send typing indicator
    try:
        client.conversations \
            .conversations(CONVERSATION_SID) \
            .typing() \
            .create(identity=None, participant_sid=None)
    except Exception as e:
        print(f"Error sending typing indicator: {e}")

    # Get bot response
    response_text = get_response_to_message(user_message, to_number)

    # Send actual message
    try:
        client.conversations \
            .conversations(CONVERSATION_SID) \
            .messages \
            .create(author=f"{TWILIO_PHONE_NUMBER}", body=response_text)
    except Exception as e:
        print(f"Error sending message: {e}")

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
