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
    handlers=[logging.StreamHandler(sys.stdout)],  # Explicitly use stdout
)

logger = logging.getLogger(__name__)


load_csv_data()


policy_data = get_grouped_policy_data()

# with open("policy_data5.json", encoding="utf-8", mode="w") as c:
#     r = json.dumps(policy_data, indent=2, ensure_ascii=False)
#     c.write(r)

sura_downloader = SuraDownloader(PolicyDriver(headless=False))

# Example of how to access the data
for company, policies in policy_data.items():
    # print(f"Company: {company}")
    if company != "SURA":
        continue
    random_items = random.sample(policies, min(3, len(policies)))
    sura_downloader.process_policies(random_items)
    for policy in random_items:
        # TODO: design database/update database
        # print(f"  Policy: {policy['number']}, Expires: {policy['expiration_date']}")
        # expiration_year = policy['expiration_date'].split('/')[-1]
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
