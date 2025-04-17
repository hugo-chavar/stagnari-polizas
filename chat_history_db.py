import sqlite3
from typing import List, Tuple
import os

DATABASE_NAME = "chat_history.db"

def init_db():
    """Initialize the database and create tables if they don't exist"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            client_number TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()

def save_message(client_number: str, role: str, content: str):
    """Save a message to the database"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (client_number, role, content) VALUES (?, ?, ?)",
            (client_number, role, content)
        )
        conn.commit()

def get_client_history(client_number: str) -> List[Tuple[str, str]]:
    """Retrieve all messages for a specific client"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM chat_history WHERE client_number = ? ORDER BY timestamp",
            (client_number,)
        )
        return cursor.fetchall()

# Initialize the database when this module is imported
init_db()