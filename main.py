from fastapi import FastAPI, Request, Response
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from message_processor import generate_response
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

    bot_response = generate_response(incoming_message)
    response.message(bot_response)

    # Return the TwiML response with the correct Content-Type header
    return Response(content=str(response), media_type="application/xml")

@app.get("/")
def read_root():
    return {"message": "Hello World"}