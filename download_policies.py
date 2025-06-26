import json
import logging
import sys
import random
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="sura_downloader_test1.log",
    force=True,
)
# handlers=[logging.StreamHandler(sys.stdout)],  # Explicitly use stdout

import chat_history_db as db
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
    policy_db = db.get_policy_with_cars(company, policy)
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
        # TODO: design database/update database
        results.append(policy)
        log_policy(company, policy)

    results_sorted = sorted(results, key=lambda policy: policy["number"])
    with open("policy_results.json", encoding="utf-8", mode="w") as c:
        r = json.dumps(results, indent=2, ensure_ascii=False)
        c.write(r)
