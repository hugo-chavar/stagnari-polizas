import logging
import os
import re
import pandas as pd
from datetime import datetime, timedelta

from gsheets import export_sheet_to_csv
from filter_utils import relax_cliente_filter_level1, relax_cliente_filter_level2, relax_telefono_filter, relax_marca_filter

UPDATE_INTERVAL_FILE = os.getenv('UPDATE_INTERVAL_FILE')
UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL'))

GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
CSV_FILE_PATH= os.getenv("CSV_FILE_PATH")

df = None
last_update = None

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",  # Controls the non-millisecond part
)

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
        logger.info("UPDATE_INTERVAL has passed - performing updates...")
        export_sheet_to_csv(GOOGLE_SHEET_URL, GOOGLE_SHEET_NAME, CSV_FILE_PATH)
        update_interval()
    else:
        logger.info("UPDATE_INTERVAL has not passed yet - skipping updates")
    
    df = pd.read_csv(CSV_FILE_PATH)

def remove_words(list, words):
    pattern = r'\b(?:' + '|'.join(map(re.escape, words)) + r')\b'
    cleaned_list = []
    for text in list:
        # Remove suffix and replace multiple spaces with a single space
        cleaned_text = re.sub(r' +', ' ', re.sub(pattern, '', text).strip())
        cleaned_list.append(cleaned_text)
    return cleaned_list

def get_surnames_prompt():
    """
    Return a prompt to fix spelling mistakes in surnames and company names.
    """
    global df
    # Extract 'Cliente' column, ensuring non-null string values
    client_series = df["Cliente"].dropna().astype(str)
    # Remove content after first comma and trim
    names = [s for s in client_series if "," in s]
    surnames = [s.split(",")[0].strip().upper() for s in names]
    all_surnames = [s for s in " ".join(surnames).split() if len(s) > 2]
    companies = [s for s in client_series if "," not in s]
    companies = [s.replace("(", "").replace(")", "") for s in companies]
    companies = [s.replace('"', '').replace('.', ' ') for s in companies]

    words_to_remove = ["SA", "SRL", "SAS", "LTDA", "SUC", "-", "CIA", "&"]

    cleaned_companies = remove_words(companies, words_to_remove)
    
    sorted_surnames = sorted({s.upper() for s in all_surnames}, key=lambda s: s.upper())
    companies_str = ",".join(cleaned_companies)
    surnames_str = ",".join(sorted_surnames)
    prompt = f"""Automatically fix user's spelling mistakes for the Cliente column. Example: If user asks for "Ruiz" create a query that includes "Ruis". This is the list of surnames and companies in the database:
Companies: {companies_str}
Surnames: {surnames_str}
If you don't find a a good match relax the filter so it can catch more results. For example, if user asks for "Ruiz", use "Rui" to include more results.
"""
    
    return prompt

def apply_filter(query_string, columns, level=0):
    global df
    result = None
    if not query_string.strip():
        raise ValueError("Too many records to filter. Please provide a more specific query.")
        # if columns:
        #     result = df[columns]
        # else:
        #     result = df
    else:
        query_string = query_string.replace("true", "True")
        query_string = query_string.replace("false", "False")
        if columns:
            try:
                # Fix old error
                i = columns.index("Referencia")
                columns[i] = "Poliza"
            except ValueError:
                pass
            result = df.query(query_string, engine='python')[columns]
        else:
            result = df.query(query_string, engine='python')
    csv_string = result.to_csv(index=False, lineterminator ='\n')
    logger.info("Filtered data:")
    logger.info(csv_string)
    line_count = csv_string.count('\n') - 1
    has_rows  = line_count > 0
    if not has_rows:
        logger.info("No rows found")

        if level == 0:
            query_change = False
            if "Cliente." in query_string:
                logger.info("Relaxing cliente filter and retrying level 1...")
                query_string = relax_cliente_filter_level1(query_string)
                query_change = True
            if "Tel1." in query_string:
                logger.info("Relaxing telefono filter and retrying level 1...")
                query_string = relax_telefono_filter(query_string)
                query_change = True
            if "Marca." in query_string:
                logger.info("Relaxing marca filter and retrying level 1...")
                query_string = relax_marca_filter(query_string)
                query_change = True
            if query_change:
                return apply_filter(query_string, columns, level=1)
        if level == 1:
            if "Cliente." in query_string:
                logger.info("Relaxing cliente filter and retrying level 2...")
                query_string = relax_cliente_filter_level2(query_string)
                return apply_filter(query_string, columns, level=2)
        if level == 2:
            if "&" in query_string or " and " in query_string:
                logger.info("Query string contains '&' - removing it")
                query_string = query_string.replace("&", "|").replace(" and ", " or ")
                return apply_filter(query_string, columns)
    return csv_string


load_csv_data()