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

def send_delayed_response(user_number: str, user_message: str):
    """Process user input and send delayed bot response."""
    try:

        response_text = get_response_to_message(user_message, user_number)

        # Send actual response
        client.messages.create(
            from_=TWILIO_PHONE_NUMBER,
            to=user_number,
            body=response_text
        )
    except Exception as e:
        print(f"Error sending delayed message: {e}", flush=True)

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
