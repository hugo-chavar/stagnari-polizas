import logging
import csv, os
import re
import pandas as pd
from datetime import datetime, timedelta
from chat_history_db import get_policy_with_cars
from gsheets import get_sheet_data
from filter_utils import (
    relax_cliente_filter_level1,
    relax_cliente_filter_level2,
    relax_telefono_filter,
    relax_marca_filter,
    relax_modelo_filter,
    weighted_fuzzy_search,
)

UPDATE_INTERVAL_FILE = os.getenv("UPDATE_INTERVAL_FILE")
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL"))

GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
CSV_FILE_PATH = os.getenv("CSV_FILE_PATH")

df = None
last_update = None

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",  # Controls the non-millisecond part
)


def sheet_data_to_csv(spreadsheet_url, sheet_name, csv_file_path):

    logger.info(f"Inicia sheet_data_to_csv. Sheet: {sheet_name}")
    try:
        data = get_sheet_data(spreadsheet_url, sheet_name)
        if data is None:
            logger.info("Failed to obtain the data from sheet")

        for row in data[1:]:
            lic_plate_value = row[data[0].index("Matricula")]
            if not lic_plate_value:
                policy_value = row[data[0].index("Poliza")]
                company_value = row[data[0].index("Compañia")]

                policy_db = get_policy_with_cars(company_value, policy_value)
                if policy_db and policy_db.contains_cars and len(policy_db.cars) == 1:
                    brand_value = row[data[0].index("Marca")]
                    car = policy_db.cars[0]
                    if (
                        car.license_plate
                        and car.brand
                        and brand_value
                        and car.brand.strip() == brand_value.strip()
                    ):

                        logger.info(
                            f"Matricula is empty or invalid. Setting to '{car.license_plate}'. Poliza: {policy_value}. Compañia {company_value}"
                        )
                        row[data[0].index("Matricula")] = car.license_plate

        with open(csv_file_path, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(data)

        logger.info(f"OK. CSV saved: {csv_file_path}")
    except Exception as e:
        logger.info(f"Error saving data sheet to CSV: {str(e)}")


def update_interval_has_passed():
    """Check if UPDATE_INTERVAL minutes have passed since last recorded timestamp."""
    try:
        # Get current time rounded to minutes
        current_time = datetime.now().replace(second=0, microsecond=0)

        # Read last update time from file
        global last_update
        if not last_update:
            with open(UPDATE_INTERVAL_FILE, "r") as f:
                last_update_str = f.read().strip()
                last_update = datetime.strptime(last_update_str, "%Y-%m-%d %H:%M:%S")

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
    with open(UPDATE_INTERVAL_FILE, "w") as f:
        f.write(last_update.strftime("%Y-%m-%d %H:%M:%S"))


def load_csv_data():
    global df
    if update_interval_has_passed():
        logger.info("UPDATE_INTERVAL has passed - performing updates...")
        sheet_data_to_csv(GOOGLE_SHEET_URL, GOOGLE_SHEET_NAME, CSV_FILE_PATH)
        update_interval()
    else:
        logger.info("UPDATE_INTERVAL has not passed yet - skipping updates")

    df = pd.read_csv(CSV_FILE_PATH)


def remove_words(list, words):
    pattern = r"\b(?:" + "|".join(map(re.escape, words)) + r")\b"
    cleaned_list = []
    for text in list:
        # Remove suffix and replace multiple spaces with a single space
        cleaned_text = re.sub(r" +", " ", re.sub(pattern, "", text).strip())
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
    companies = [s.replace('"', "").replace(".", " ") for s in companies]

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


def apply_filter(query_string, columns, query_fields, level=0):
    relaxed_query_string = query_string
    if "Cliente." in query_string:
        relaxed_query_string = relax_cliente_filter_level1(query_string)
    if "Modelo." in query_string:
        relaxed_query_string = relax_modelo_filter(relaxed_query_string)
    csv_string, has_rows = execute_filter(relaxed_query_string, columns)
    if not has_rows:
        logger.info("No rows found")

        new_level = level + 1
        if level == 0:
            query_change = False
            if "Tel1." in query_string:
                logger.info("Relaxing telefono filter and retrying level 1...")
                query_string = relax_telefono_filter(query_string)
                query_change = True
            if "Marca." in query_string:
                logger.info("Relaxing marca filter and retrying level 1...")
                query_string = relax_marca_filter(query_string)
                query_change = True
            if query_change:
                return apply_filter(
                    query_string, columns, query_fields, level=new_level
                )
            else:
                level = new_level
        if level == 1:
            if query_fields.get("Cliente"):
                query_fields["Cliente"] = query_fields.get("Cliente").replace(".*", " ")
                logger.info("Performing fuzzy search on Cliente field...")
                top_matches = weighted_fuzzy_search(
                    df, "Cliente", query_fields.get("Cliente"), top_n=5
                )
                if columns:
                    top_matches = top_matches[columns]
                csv_string, has_rows = get_csv_string(top_matches)
                if not has_rows:
                    level = new_level
                    logger.info("No rows found after fuzzy search on Cliente")
                else:
                    logger.info("Fuzzy search on Cliente found rows:")
                    logger.info(csv_string)
            elif query_fields.get("Matricula"):
                top_matches = weighted_fuzzy_search(
                    df, "Matricula", query_fields.get("Matricula"), top_n=5
                )
                if columns:
                    top_matches = top_matches[columns]
                csv_string, has_rows = get_csv_string(top_matches)
                if not has_rows:
                    level = new_level
                    logger.info("No rows found after fuzzy search on Matricula")
                else:
                    logger.info("Fuzzy search on Matricula found rows:")
                    logger.info(csv_string)
            else:
                level = new_level
                logger.info("Skipping fuzzy search")
        if level == 2:
            if "Cliente." in query_string:
                logger.info("Relaxing cliente filter and retrying level 2...")
                query_string = relax_cliente_filter_level2(query_string)
                return apply_filter(
                    query_string, columns, query_fields, level=new_level
                )
        if level == 3:
            if "&" in query_string or " and " in query_string:
                logger.info("Query string contains '&' - removing it")
                query_string = query_string.replace("&", "|").replace(" and ", " or ")
                return apply_filter(query_string, columns, query_fields)
    return csv_string


def execute_filter(query_string, columns):
    global df
    result = None
    if columns:
        result = df.query(query_string, engine="python")[columns]
    else:
        result = df.query(query_string, engine="python")
    return get_csv_string(result)


def get_csv_string(result):
    csv_string = result.to_csv(index=False, lineterminator="\n")
    line_count = csv_string.count("\n") - 1
    has_rows = line_count > 0

    # Log only up to 10 rows with ellipsis if there are more
    if has_rows:
        logger.info("Filtered data:")
        lines = csv_string.split("\n")
        if line_count > 10:
            # Take first 10 rows and add ellipsis
            shortened_lines = lines[:11]  # 10 data rows + header
            shortened_csv = "\n".join(shortened_lines) + "\n..."
            logger.info(shortened_csv)
        else:
            logger.info(csv_string)

    return csv_string, has_rows


def get_grouped_policy_data():
    global df
    # Make sure required columns exist
    required_columns = [
        "Compañia",
        "Poliza",
        "Vencimiento",
        "Matricula",
        "Marca",
        "Modelo",
        "Año",
    ]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in DataFrame")
    string_columns = ["Matricula", "Marca", "Modelo"]
    df[string_columns] = df[string_columns].fillna("")
    # Convert expiration date to datetime if it's not already
    if not pd.api.types.is_datetime64_any_dtype(df["Vencimiento"]):
        try:
            df["Vencimiento"] = pd.to_datetime(
                df["Vencimiento"], format="%d/%m/%Y", errors="coerce"
            )
        except ValueError:
            # Try alternative date formats if the primary format fails
            df["Vencimiento"] = pd.to_datetime(df["Vencimiento"], errors="coerce")

    # Drop rows where critical fields are missing
    df = df.dropna(subset=["Compañia", "Poliza"])

    # Group by company and policy
    result = {}
    bicycle_brands = ["OTRAS MARCAS", "RAVE", "GYROOR", "BIANCHI"]
    cancelled_policies = [
        "1938091",
        "1940520",
        "2123126",
        "2138316",
        "2160105",
        "2172904",
    ]

    # Iterate through each unique company
    for company in df["Compañia"].unique():
        company_df = df[df["Compañia"] == company]

        # Group by policy within the company
        policies = []
        for policy_num in company_df["Poliza"].unique():
            cancelled = policy_num in cancelled_policies
            policy_df = company_df[company_df["Poliza"] == policy_num]

            # Skip if policy_df is empty (shouldn't happen after dropna)
            if len(policy_df) == 0:
                continue

            policy_expiration = policy_df["Vencimiento"].iloc[0]

            expiration_str = None
            if not pd.isna(policy_expiration):
                # Format expiration date as string (or keep as datetime)
                expiration_str = policy_expiration.strftime("%d/%m/%Y")
                policy_year = str(policy_expiration.year)

            policy_coverage = policy_df["Cobertura"].iloc[0]
            soa_only = False
            if not pd.isna(policy_coverage):
                soa_only = policy_coverage.strip() == "SOA"

            # Get all vehicles for this policy
            vehicles = []
            contains_cars = False
            empty_license_plate = 0
            for _, row in policy_df.iterrows():
                brand = row["Marca"]
                license_plate = row["Matricula"]
                if pd.isna(license_plate):
                    license_plate = str(empty_license_plate)
                    empty_license_plate += 1
                fuel = row["Combustible"]
                if pd.isna(fuel):
                    fuel = None
                model = row["Modelo"]
                if pd.isna(model):
                    model = ""

                is_car = not (
                    "BIKE" in model or (fuel is None and brand in bicycle_brands)
                )
                contains_cars = contains_cars or is_car
                vehicle = {
                    "license_plate": license_plate,
                    "brand": brand,
                    "model": row["Modelo"],
                    "year": row["Año"],
                }

                vehicles.append(vehicle)

            # Create policy dictionary
            policy = {
                "number": policy_num,
                "year": policy_year,
                "expiration_date": expiration_str,
                "contains_cars": contains_cars,
                "vehicles": vehicles,
                "soa_only": soa_only,
                "cancelled": cancelled,
            }
            policies.append(policy)

        # Add company to result only if it has policies
        if policies:
            result[company] = policies

    return result


load_csv_data()
