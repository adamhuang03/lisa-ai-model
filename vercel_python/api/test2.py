import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from custom_lib.cookies_extractor_async import cookie_extractor_from_json
from custom_lib.automail_ai_craft import LinkedinWrapper, enrich_person_more
from custom_lib.automail_ai_search_v2 import search_people
from dotenv import load_dotenv
import json
import requests

load_dotenv()

with open('multi_cookies/cookies_A1.json', 'r') as f:
    cookies_C5 = json.load(f)

res = requests.post(
    'http://127.0.0.1:8000/get-geo-id',
    json={
        "input": "New York",
        "cookies": cookies_C5
    }
)

json_data = res.json()

print(json_data)

# cookies_jar = cookie_extractor_from_json(cookies_C5)
# linkedin = LinkedinWrapper(os.getenv("LINKEDIN_USER_1"), os.getenv("LINKEDIN_PASS_1"), cookies=cookies_jar, debug=True)

# result = linkedin.get_profile(
#         public_id="steven-menhorn",
#     )

# print(json.dumps(result, indent=4))

# with open('save.json', 'w') as f:
#     import json
#     json.dump(result, f, indent=4)