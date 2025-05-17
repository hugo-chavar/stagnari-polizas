import os
from fastapi import HTTPException, Depends
from dotenv import load_dotenv
import bcrypt
from pydantic import BaseModel

# Load environment variables
load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")

class Item(BaseModel):
    user_name: str
    user_password: str

# Function to verify the password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# Dependency injection for authentication
def verify_admin(item: Item) -> Item:
    if item.user_name == ADMIN_USERNAME and verify_password(item.user_password, ADMIN_PASSWORD_HASH):
        return item
    raise HTTPException(status_code=401, detail="Unauthorized")
