from fastapi import FastAPI, Request, Response, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from twilio.rest import Client
from pydantic import BaseModel
from auth import verify_admin
from message_processor import get_response_to_message
from chat_history_db import (
    get_client_history,
    get_query_history,
    cleanup_old_messages,
    add_user,
    get_user,
    get_all_users,
)
from split_messages import split_long_message
from files_finder import find_files

import os
import time

app = FastAPI()
security = HTTPBasic()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "https://hugo-chavar.github.io"],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
SHARED_FILES_URL = os.getenv("SHARED_FILES_URL")

client = Client(ACCOUNT_SID, AUTH_TOKEN)


def send_delayed_response(user_number: str, user_message: str):
    """Process user input and send delayed bot response."""
    try:

        response_text, files_to_send = get_response_to_message(
            user_message, user_number
        )
        if response_text:
            all_messages = split_long_message(response_text)

            for message in all_messages:
                # Send the message with a delay
                send_message(user_number, message)
                # Add a delay of 5 seconds between messages
                time.sleep(5)
        if files_to_send:
            for file in files_to_send:
                send_file(user_number, file["path"], file["name"])
                time.sleep(5)
    except ValueError as ve:
        print(f"ValueError: {ve}", flush=True)
        send_message(user_number, str(ve))
    except Exception as e:
        print(f"Error sending delayed message: {e}", flush=True)


def send_message(user_number, message):
    client.messages.create(from_=TWILIO_PHONE_NUMBER, to=user_number, body=message)
    print(f"Sent message: {message} to {user_number}", flush=True)


def send_file(user_number, file_path, body="Requested document"):
    public_url = f"{SHARED_FILES_URL}/{file_path}"

    client.messages.create(
        from_=TWILIO_PHONE_NUMBER,
        to=user_number,
        media_url=[public_url],
        body=body,
    )
    print(f"Sent file: {public_url} to {user_number}", flush=True)


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    form_data = await request.form()
    incoming_message = form_data.get("Body", "").lower()
    sender_number = form_data.get("From", "")

    if get_user(sender_number) is None:
            background_tasks.add_task(send_message, sender_number, "No autorizado")
    else:
        background_tasks.add_task(
            send_delayed_response, sender_number, incoming_message
        )

    return Response(status_code=200)


class Item(BaseModel):
    message: str
    number: str


@app.get("/")
def read_root(credentials: HTTPBasicCredentials = Depends(security)):
    if verify_admin(credentials):
        print(str(SHARED_FILES_URL))
        return {"message": "Hello Admin"}


@app.post("/q")
def answer_question(item: Item, credentials: HTTPBasicCredentials = Depends(security)):
    if verify_admin(credentials):
        if item.message.lower().strip() == "test":
            bot_response = 'Los autos asociados a clientes con el apellido "Pepito" son:  \n\n1. *PEPITO, WALTER Y PEPITA, SUSANA*:  \n   - FORD NEW 208 ALLURE 1.2 EXTRA FULL (2017, NAFTA, SCH8879)  \n   - FORD (1980, DIESEL, YUI6855)  \n   - TOYOTA RAV4 2.5 LIMITED PLUS HYBRID 4X4 (2034, NAFTA, TTT8998)  \n   - TOYOTA HILUX 3.0 SRV 4X2 (2013, DIESEL, QWE6545)  \n\n2. *TEST PEPITO, GUSTAVO ADOLFO*:  \n   - TRAILER TRANSPORTADOR DE ANIMALES (2015, sin combustible, OBO587)  \n   - CHEVROLET S 10 CTDI LT 4X4 2.8 AUT. (2023, DIESEL, OAE6054)  \n\n3. *TEST PEPITO, GIANELLA*:  \n   - MASERATI GHIBLI 3.0 (2017, NAFTA, DJK5583)  \n\n4. *SHACK PEPITO, MARIA VICTORIA*:  \n   - TOYOTA PRIUS C 1.5 HIBRIDO EXTRA FULL AUT. (2018, ELECTRONICOS, SCN5281)  \n   - NISSAN KICKS EXCLUSIVE 1.6 CVT AUT. (2021, NAFTA, ERT4578)  \n\n5. *TEST PEPITO, MARTIN Fernando*:  \n   - TOYOTA COROLLA CROSS HYBRID 1.8 SE-G AUT. (2023, NAFTA, SDB4115)  \n   - TOYOTA COROLLA 1.8 DLX (1986, DIESEL, PRP7993)  \n\n6. *TEST PEPITO, FEDERICO BERNARDO*:  \n   - VOLKSWAGEN GOL GP POWER 1.6 A/A (2013, NAFTA, EWE7385)'
        else:
            try:
                bot_response, _ = get_response_to_message(item.message, item.number)
            except ValueError as ve:
                print(f"ValueError: {ve}", flush=True)
                bot_response = str(ve)
        return {"response": {bot_response}}


@app.get("/client-history")
def client_history_endpoint(
    item: Item, credentials: HTTPBasicCredentials = Depends(security)
):
    if verify_admin(credentials):
        history = get_client_history(item.number)
        return {"client_history": history}


@app.get("/query-history")
def query_history_endpoint(
    item: Item, credentials: HTTPBasicCredentials = Depends(security)
):
    if verify_admin(credentials):
        history = get_query_history(item.number)
        return {"query_history": history}


@app.post("/delete-history")
def delete_history(credentials: HTTPBasicCredentials = Depends(security)):
    if verify_admin(credentials):
        cleanup_old_messages()
        return {"status": "OK"}


class User(BaseModel):
    name: str
    number: str


@app.post("/add-user")
def add_authorized_user(
    user: User, credentials: HTTPBasicCredentials = Depends(security)
):
    if verify_admin(credentials):
        if add_user(f"whatsapp:+{user.number}", user.name):
            return {"status": f"El usuario {user.name} fue autorizado"}
        return {"status": "Error: Ya existe un usuario con ese número"}


@app.get("/get-users")
def get_users(credentials: HTTPBasicCredentials = Depends(security)):
    if verify_admin(credentials):
        users = get_all_users()
        return {"users": users}


@app.post("/sf")
def send_files(
    item: Item,
    background_tasks: BackgroundTasks,
    credentials: HTTPBasicCredentials = Depends(security),
):
    if verify_admin(credentials):
        policy_number = item.message.strip()
        license_plate = item.number.strip()
        user_wants_soa = policy_number[0] == "2"
        user_wants_mcs = policy_number[1] == "1"
        sender_number = "whatsapp:+5491134837950"
        ok, msg, soa, mcs = find_files(
            "SURA", policy_number, license_plate, user_wants_mcs
        )

        if not ok:
            bot_response = msg
        else:
            if user_wants_soa:
                bot_response = "Enviando: SOA"
                background_tasks.add_task(
                    send_file, sender_number, soa, "Certificado SOA"
                )
            if user_wants_mcs:
                bot_response += ", Mercosur"
                background_tasks.add_task(
                    send_file, sender_number, mcs, "Certificado Mercosur"
                )
        return {"response": bot_response}

@app.get("/health")
def health_check():
    # Add critical checks here (e.g., DB, Redis, etc.)
    return Response(status_code=200)
