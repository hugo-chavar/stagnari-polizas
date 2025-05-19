import sqlite3
from typing import List, Tuple
import os
from datetime import datetime, timedelta

DATABASE_NAME = "chat_history.db"

def init_db():
    """Initialize the database and create tables if they don't exist"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        # Chat history table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            client_number TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # Add index for better performance on client_number and timestamp queries
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_client_timestamp 
        ON chat_history (client_number, timestamp)
        """)
        # Query history table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            client_number TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # Add index for better performance on client_number and timestamp queries
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_client_query_timestamp 
        ON query_history (client_number, timestamp)
        """)
        # User table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user (
            client_number TEXT,
            name TEXT,
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

def save_query(client_number: str, role: str, content: str):
    """Save a query to the database"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO query_history (client_number, role, content) VALUES (?, ?, ?)",
            (client_number, role, content)
        )
        conn.commit()

def get_client_history(client_number: str, days_limit: int = 2) -> List[Tuple[str, str]]:
    """Retrieve messages for a specific client from the last N days"""
    cutoff_date = datetime.now() - timedelta(days=days_limit)
    
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT role, content FROM chat_history 
            WHERE client_number = ? 
            AND timestamp >= ?
            ORDER BY timestamp""",
            (client_number, cutoff_date.strftime("%Y-%m-%d %H:%M:%S"))
        )
        return cursor.fetchall()

def get_query_history(client_number: str, days_limit: int = 2) -> List[Tuple[str, str]]:
    """Retrieve query messages for a specific client from the last N days"""
    cutoff_date = datetime.now() - timedelta(days=days_limit)
    
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT role, content FROM query_history 
            WHERE client_number = ? 
            AND timestamp >= ?
            ORDER BY timestamp""",
            (client_number, cutoff_date.strftime("%Y-%m-%d %H:%M:%S"))
        )
        return cursor.fetchall()

def cleanup_old_messages(days_to_keep: int = 2):
    """Clean up messages older than N days"""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM chat_history WHERE timestamp < ?",
            (cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),)
        )
        cursor.execute(
            "DELETE FROM query_history WHERE timestamp < ?",
            (cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),)
        )
        conn.commit()
        return cursor.rowcount  # Returns number of deleted rows

def add_user(client_number: str, name: str) -> bool:
    """Add a new user to the database"""
    if get_user(client_number) is not None:
        return False
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (client_number, name) VALUES (?, ?)",
            (client_number, name)
        )
        conn.commit()
        return True
        
def get_user(client_number: str) -> str:
    """Retrieve user information"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM user WHERE client_number = ?",
            (client_number,)
        )
        result = cursor.fetchone()
        return result[0] if result else None

def get_all_users() -> List[str]:
    """Retrieve all users"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, client_number FROM user")
        return [row[0] for row in cursor.fetchall()]

# Initialize the database when this module is imported
init_db()