import sqlite3
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from datetime import datetime, timedelta, date
from .models import Policy, Car

DATABASE_NAME = "chat_history.db"


def init_db():
    """Initialize the database and create tables if they don't exist"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        # Chat history table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS chat_history (
            client_number TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        # Add index for better performance on client_number and timestamp queries
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_client_timestamp 
        ON chat_history (client_number, timestamp)
        """
        )
        # Query history table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS query_history (
            client_number TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        # Add index for better performance on client_number and timestamp queries
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_client_query_timestamp 
        ON query_history (client_number, timestamp)
        """
        )
        # User table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS user (
            client_number TEXT,
            name TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        # Car table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS car (
            company TEXT,
            policy_number TEXT,
            license_plate TEXT,
            brand TEXT,
            model TEXT,
            year INTEGER,
            soa_file_path TEXT,
            mercosur_file_path TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (company, policy_number, license_plate)
        )
        """
        )
        # Policy table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS policy (
            company TEXT,
            policy_number TEXT,
            year INTEGER,
            expiration_date DATE,
            downloaded BOOLEAN,
            contains_cars BOOLEAN,
            soa_only BOOLEAN,
            obs TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (company, policy_number)
        )
        """
        )
        conn.commit()


def save_message(client_number: str, role: str, content: str):
    """Save a message to the database"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (client_number, role, content) VALUES (?, ?, ?)",
            (client_number, role, content),
        )
        conn.commit()


def save_query(client_number: str, role: str, content: str):
    """Save a query to the database"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO query_history (client_number, role, content) VALUES (?, ?, ?)",
            (client_number, role, content),
        )
        conn.commit()


def get_client_history(
    client_number: str, days_limit: int = 2
) -> List[Tuple[str, str]]:
    """Retrieve messages for a specific client from the last N days"""
    cutoff_date = datetime.now() - timedelta(days=days_limit)

    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT role, content FROM chat_history 
            WHERE client_number = ? 
            AND timestamp >= ?
            ORDER BY timestamp""",
            (client_number, cutoff_date.strftime("%Y-%m-%d %H:%M:%S")),
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
            (client_number, cutoff_date.strftime("%Y-%m-%d %H:%M:%S")),
        )
        return cursor.fetchall()


def cleanup_old_messages(days_to_keep: int = 2):
    """Clean up messages older than N days"""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)

    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM chat_history WHERE timestamp < ?",
            (cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),),
        )
        cursor.execute(
            "DELETE FROM query_history WHERE timestamp < ?",
            (cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),),
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
            (client_number, name),
        )
        conn.commit()
        return True


def get_user(client_number: str) -> str:
    """Retrieve user information"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM user WHERE client_number = ?", (client_number,)
        )
        result = cursor.fetchone()
        return result[0] if result else None


def get_all_users() -> List[str]:
    """Retrieve all users"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, client_number FROM user")
        return cursor.fetchall()


def add_car(
    company: str,
    policy_number: str,
    license_plate: str,
    brand: str,
    model: str,
    year: int,
    soa_file_path: str = None,
    mercosur_file_path: str = None,
) -> bool:
    """Add a new car to the database"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO car (company, policy_number, license_plate, brand, model, year, soa_file_path, mercosur_file_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    company,
                    policy_number,
                    license_plate,
                    brand,
                    model,
                    year,
                    soa_file_path,
                    mercosur_file_path,
                ),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Car already exists


def update_car(
    company: str,
    policy_number: str,
    license_plate: str,
    brand: str = None,
    model: str = None,
    year: int = None,
    soa_file_path: str = None,
    mercosur_file_path: str = None,
) -> bool:
    """Update an existing car's information"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        fields = []
        values = []

        if brand is not None:
            fields.append("brand = ?")
            values.append(brand)
        if model is not None:
            fields.append("model = ?")
            values.append(model)
        if year is not None:
            fields.append("year = ?")
            values.append(year)
        if soa_file_path is not None:
            fields.append("soa_file_path = ?")
            values.append(soa_file_path)
        if mercosur_file_path is not None:
            fields.append("mercosur_file_path = ?")
            values.append(mercosur_file_path)

        if not fields:
            return False  # No fields to update

        # Add timestamp update
        fields.append("timestamp = CURRENT_TIMESTAMP")

        values.append(company)
        values.append(policy_number)
        values.append(license_plate)

        query = f"UPDATE car SET {', '.join(fields)} WHERE company = ? AND policy_number = ? AND license_plate = ?"

        cursor.execute(query, tuple(values))
        conn.commit()

        return cursor.rowcount > 0  # Returns True if any row was updated


def get_car(
    policy_number: str, license_plate: str
) -> Tuple[str, str, str, int, str, str]:
    """Retrieve car information by policy number and license plate"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT brand, model, year, soa_file_path, mercosur_file_path FROM car WHERE policy_number = ? AND license_plate = ?",
            (policy_number, license_plate),
        )
        result = cursor.fetchone()
        return result if result else None


def insert_policy(policy: Policy) -> None:
    """Insert a new policy into the database"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO policy (
                company, policy_number, year, expiration_date,
                downloaded, contains_cars, soa_only, obs
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                policy.company,
                policy.policy_number,
                policy.year,
                policy.expiration_date,
                policy.downloaded,
                policy.contains_cars,
                policy.soa_only,
                policy.obs,
            ),
        )
        conn.commit()


def get_policy(company: str, policy_number: str) -> Optional[Policy]:
    """Retrieve a policy by company and policy number"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row  # To access columns by name
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 
                company, policy_number, year, expiration_date,
                downloaded, contains_cars, soa_only, obs, timestamp
            FROM policy
            WHERE company = ? AND policy_number = ?
            """,
            (company, policy_number),
        )
        row = cursor.fetchone()
        if row:
            return Policy(
                company=row["company"],
                policy_number=row["policy_number"],
                year=row["year"],
                expiration_date=date.fromisoformat(row["expiration_date"]),
                downloaded=bool(row["downloaded"]),
                contains_cars=bool(row["contains_cars"]),
                soa_only=bool(row["soa_only"]),
                obs=row["obs"],
                timestamp=(
                    datetime.fromisoformat(row["timestamp"])
                    if row["timestamp"]
                    else None
                ),
            )
        return None


def insert_car(car: Car) -> None:
    """Insert a new car into the database"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO car (
                company, policy_number, license_plate,
                brand, model, year,
                soa_file_path, mercosur_file_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                car.company,
                car.policy_number,
                car.license_plate,
                car.brand,
                car.model,
                car.year,
                car.soa_file_path,
                car.mercosur_file_path,
            ),
        )
        conn.commit()


def get_cars_by_policy(company: str, policy_number: str) -> List[Car]:
    """Retrieve all cars for a specific policy"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 
                company, policy_number, license_plate,
                brand, model, year,
                soa_file_path, mercosur_file_path, timestamp
            FROM car
            WHERE company = ? AND policy_number = ?
            """,
            (company, policy_number),
        )
        return [
            Car(
                company=row["company"],
                policy_number=row["policy_number"],
                license_plate=row["license_plate"],
                brand=row["brand"],
                model=row["model"],
                year=row["year"],
                soa_file_path=row["soa_file_path"],
                mercosur_file_path=row["mercosur_file_path"],
                timestamp=(
                    datetime.fromisoformat(row["timestamp"])
                    if row["timestamp"]
                    else None
                ),
            )
            for row in cursor.fetchall()
        ]


def get_policy_with_cars(company: str, policy_number: str) -> Optional[Policy]:
    """Get a policy with its cars in one query"""
    policy = get_policy(company, policy_number)
    if policy and policy.contains_cars:
        policy.load_cars()
    return policy


# Initialize the database when this module is imported
init_db()
