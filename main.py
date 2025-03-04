from fastapi import FastAPI, Request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Get Twilio credentials from environment variables
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Initialize Twilio client
client = Client(ACCOUNT_SID, AUTH_TOKEN)

@app.post("/webhook")
async def webhook(request: Request):
    form_data = await request.form()
    incoming_message = form_data.get("Body", "").lower()
    sender_number = form_data.get("From", "")

    # Create a response object
    response = MessagingResponse()

    # Simple bot logic
    if "hello" in incoming_message:
        response.message("Hi there! How can I help you?")
    elif "bye" in incoming_message:
        response.message("Goodbye! Have a great day!")
    else:
        response.message("I'm sorry, I didn't understand that.")

    # Return the TwiML response
    return str(response)

@app.get("/")
def read_root():
    return {"message": "Hello World"}