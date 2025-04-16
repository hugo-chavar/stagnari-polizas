import os
import pandas as pd
from datetime import datetime, timedelta

from gsheets import export_sheet_to_csv

UPDATE_INTERVAL_FILE = os.getenv('UPDATE_INTERVAL_FILE')
UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL'))

GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
CSV_FILE_PATH= os.getenv("CSV_FILE_PATH")

df = None
last_update = None


def update_interval_has_passed():
    """Check if UPDATE_INTERVAL minutes have passed since last recorded timestamp."""
    try:
        # Get current time rounded to minutes
        current_time = datetime.now().replace(second=0, microsecond=0)
        
        # Read last update time from file
        global last_update
        if not last_update:
            with open(UPDATE_INTERVAL_FILE, 'r') as f:
                last_update_str = f.read().strip()
                last_update = datetime.strptime(last_update_str, '%Y-%m-%d %H:%M:%S')
        
        # Calculate time difference
        time_diff = current_time - last_update
        return time_diff >= timedelta(minutes=UPDATE_INTERVAL)
    
    except (FileNotFoundError, ValueError):
        # File doesn't exist or is empty/corrupt - treat as interval passed
        return True


def update_interval():
    """Update the timestamp file with current time (rounded to minutes)."""
    global last_update
    last_update = datetime.now().replace(second=0, microsecond=0)
    with open(UPDATE_INTERVAL_FILE, 'w') as f:
        f.write(last_update.strftime('%Y-%m-%d %H:%M:%S'))


def load_csv_data():
    global df
    if update_interval_has_passed():
        print("UPDATE_INTERVAL has passed - performing updates...")
        export_sheet_to_csv(GOOGLE_SHEET_URL, GOOGLE_SHEET_NAME, CSV_FILE_PATH)
        update_interval()
    else:
        print("UPDATE_INTERVAL has not passed yet - skipping updates")
    
    df = pd.read_csv(CSV_FILE_PATH)


def apply_filter(query_string, columns):
    global df
    result = None
    if not query_string:
        result = df[columns]
    else:
        result = df.query(query_string, engine='python')[columns]
    csv_string = result.to_csv(index=False, lineterminator ='\n')
    print("Filtered data:")
    print(csv_string)
    return csv_string
