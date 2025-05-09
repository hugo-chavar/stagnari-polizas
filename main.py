from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from twilio.rest import Client
from pydantic import BaseModel
from message_processor import get_response_to_message
from chat_history_db import get_client_history, get_query_history, cleanup_old_messages

import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "https://hugo-chavar.github.io"
        ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

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
    if item.message.lower().strip() == "test":
        bot_response = "Los autos asociados a clientes con el apellido \"Pepito\" son:  \n\n1. *PEPITO, WALTER Y PEPITA, SUSANA*:  \n   - FORD NEW 208 ALLURE 1.2 EXTRA FULL (2017, NAFTA, SCH8879)  \n   - FORD (1980, DIESEL, YUI6855)  \n   - TOYOTA RAV4 2.5 LIMITED PLUS HYBRID 4X4 (2034, NAFTA, TTT8998)  \n   - TOYOTA HILUX 3.0 SRV 4X2 (2013, DIESEL, QWE6545)  \n\n2. *TEST PEPITO, GUSTAVO ADOLFO*:  \n   - TRAILER TRANSPORTADOR DE ANIMALES (2015, sin combustible, OBO587)  \n   - CHEVROLET S 10 CTDI LT 4X4 2.8 AUT. (2023, DIESEL, OAE6054)  \n\n3. *TEST PEPITO, GIANELLA*:  \n   - MASERATI GHIBLI 3.0 (2017, NAFTA, DJK5583)  \n\n4. *SHACK PEPITO, MARIA VICTORIA*:  \n   - TOYOTA PRIUS C 1.5 HIBRIDO EXTRA FULL AUT. (2018, ELECTRONICOS, SCN5281)  \n   - NISSAN KICKS EXCLUSIVE 1.6 CVT AUT. (2021, NAFTA, ERT4578)  \n\n5. *TEST PEPITO, MARTIN Fernando*:  \n   - TOYOTA COROLLA CROSS HYBRID 1.8 SE-G AUT. (2023, NAFTA, SDB4115)  \n   - TOYOTA COROLLA 1.8 DLX (1986, DIESEL, PRP7993)  \n\n6. *TEST PEPITO, FEDERICO BERNARDO*:  \n   - VOLKSWAGEN GOL GP POWER 1.6 A/A (2013, NAFTA, EWE7385)"
    else:
        bot_response = get_response_to_message(item.message, item.number)
    return {"response": {bot_response}}

@app.get("/client-history")
def client_history_endpoint(item: Item):
    history = get_client_history(item.number)
    return {"client_history": history}

@app.get("/query-history")
def query_history_endpoint(item: Item):
    history = get_query_history(item.message)
    return {"query_history": history}

@app.post("/delete-history")
def delete_history():
    cleanup_old_messages()
    return {"status": "OK"}
