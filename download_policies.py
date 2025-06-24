import json
import logging
import sys
import random
from policy_data import get_grouped_policy_data, load_csv_data, df
from sura_downloader import SuraDownloader
from policy_driver import PolicyDriver


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="sura_downloader_test1.log",
    # handlers=[logging.StreamHandler(sys.stdout)],  # Explicitly use stdout
)

logger = logging.getLogger(__name__)


load_csv_data()


policy_data = get_grouped_policy_data()

# with open("all_policy_data.json", encoding="utf-8", mode="w") as c:
#     r = json.dumps(policy_data, indent=2, ensure_ascii=False)
#     c.write(r)

results = []
with open("policy_results2.json", encoding="utf-8", mode="r") as c:
    results = json.load(c)

sura_downloader = SuraDownloader(PolicyDriver(headless=False))

# Example of how to access the data
for company, policies in policy_data.items():
    # print(f"Company: {company}")
    if company != "SURA":
        continue
    random_items = random.sample(policies, min(3, len(policies)))
    with open("policy_input.json", encoding="utf-8", mode="w") as c:
        r = json.dumps(random_items, indent=2, ensure_ascii=False)
        c.write(r)
    ## remove already downloaded policies
    existing_policy_numbers = [p["number"] for p in results]
    random_items = [
        item for item in random_items if item["number" not in existing_policy_numbers]
    ]
    sura_downloader.process_policies(random_items)
    for policy in random_items:
        # TODO: design database/update database
        results.append(policy)
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

    results_sorted = sorted(results, key=lambda policy: policy["number"])
    with open("policy_results.json", encoding="utf-8", mode="w") as c:
        r = json.dumps(results, indent=2, ensure_ascii=False)
        c.write(r)
