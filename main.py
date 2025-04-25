from fastapi import FastAPI, Request, Response, BackgroundTasks
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from pydantic import BaseModel
from message_processor import get_response_to_message
from chat_history_db import get_client_history, get_query_history

import os

app = FastAPI()

# Get Twilio credentials from environment variables
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Initialize Twilio client
client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_delayed_response(to_number: str, user_message: str):
    """Background task to process and send delayed message."""
    response_text = get_response_to_message(user_message, to_number)
    client.messages.create(
        body=response_text,
        from_=TWILIO_PHONE_NUMBER,
        to=to_number
    )

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    form_data = await request.form()
    incoming_message = form_data.get("Body", "").lower()
    sender_number = form_data.get("From", "")

    # Create a response object
    response = MessagingResponse()
    response.message("Ok! Aguardame unos instantes ...")

    # Add background task to send full response
    background_tasks.add_task(send_delayed_response, sender_number, incoming_message)

    # Return the TwiML response with the correct Content-Type header
    return Response(content=str(response), media_type="application/xml")

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
