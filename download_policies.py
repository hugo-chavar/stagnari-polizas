import json
import logging
import sys
import random
import sqlite3
from datetime import datetime
from typing import List, Dict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="sura_downloader_test1.log",
    force=True,
)
# handlers=[logging.StreamHandler(sys.stdout)],  # Explicitly use stdout

import chat_history_db as db
from models import Policy, Car
from policy_data import get_grouped_policy_data, load_csv_data
from sura_downloader import SuraDownloader
from policy_driver import PolicyDriver


def log_policy(company, policy):
    try:
        if not policy["obs"]:
            for car in policy["vehicles"]:
                print(
                    f"{company}/{policy['number']}/{car['license_plate']}/{policy['year']}"
                )
        else:
            print(f"{company}/{policy['number']}/{policy["obs"]}")
    except Exception as e:
        print(f"Error in: {policy}")
        print(str(e))
        logging.exception("Detailed error:")


def need_to_be_processed(company, policy):
    policy_db = db.get_policy_with_cars(company, policy["number"])
    policy["db"] = policy_db
    if not policy_db:
        return True

    new_policy_exp_date = datetime.strptime(
        policy["expiration_date"], "%d/%m/%Y"
    ).date()

    if new_policy_exp_date > policy_db.expiration_date:
        return True

    if not policy_db.downloaded:
        return True

    return False


def insert_processed_policies(company: str, policies: List[Dict]) -> None:
    """
    Insert processed policies using existing database functions.
    Handles:
    - Date parsing from "dd/mm/yyyy"
    - Field filtering
    - Policy and vehicle insertion
    - Error handling
    """
    for policy_data in policies:
        try:
            expiration_date = datetime.strptime(
                policy_data["expiration_date"], "%d/%m/%Y"
            ).date()

            policy = Policy(
                company=company,
                policy_number=policy_data["number"],
                year=int(policy_data["year"]),
                expiration_date=expiration_date,
                downloaded=policy_data.get("downloaded", False),
                contains_cars=policy_data.get("contains_cars", False),
                soa_only=policy_data.get("soa_only", False),
                obs=policy_data.get("obs", ""),
            )

            db.insert_policy(policy)

            for vehicle_data in policy_data.get("vehicles", []):
                car = Car(
                    company=company,
                    policy_number=policy_data["number"],
                    license_plate=vehicle_data["license_plate"],
                    brand=vehicle_data["brand"],
                    model=vehicle_data["model"],
                    year=vehicle_data["year"],
                    soa_file_path=vehicle_data.get("soa"),
                    mercosur_file_path=vehicle_data.get("mercosur"),
                )
                db.insert_car(car)

        except ValueError as e:
            print(f"Skipping policy {policy_data.get('number')} due to error: {e}")
        except KeyError as e:
            print(f"Skipping policy due to missing field: {e}")
        except sqlite3.Error as e:
            print(f"Database error with policy {policy_data.get('number')}: {e}")


logger = logging.getLogger(__name__)

load_csv_data()

policy_data = get_grouped_policy_data()

new_policy_data = {}

for company, policies in policy_data.items():

    kept_policies = [p for p in policies if need_to_be_processed(company, p)]
    if kept_policies:
        new_policy_data[company] = kept_policies

results = []
with open("policy_results.json", encoding="utf-8", mode="r") as c:
    results = json.load(c)

sura_downloader = SuraDownloader(PolicyDriver(headless=False))

for company, policies in new_policy_data.items():
    if company != "SURA":
        continue
    # random_items = random.sample(policies, min(3, len(policies)))
    random_items = [i for i in policies if i["number"] == "2121199"]
    with open("policy_input.json", encoding="utf-8", mode="w") as c:
        r = json.dumps(random_items, indent=2, ensure_ascii=False)
        c.write(r)
    ## remove already downloaded policies
    existing_policy_numbers = [p["number"] for p in results]
    random_items = [
        item for item in random_items if item["number"] not in existing_policy_numbers
    ]
    sura_downloader.process_policies(random_items)
    for policy in random_items:
        results.append(policy)
        log_policy(company, policy)
        insert_processed_policies(company, random_items)

    results_sorted = sorted(results, key=lambda policy: policy["number"])
    with open("policy_results.json", encoding="utf-8", mode="w") as c:
        r = json.dumps(results, indent=2, ensure_ascii=False)
        c.write(r)
