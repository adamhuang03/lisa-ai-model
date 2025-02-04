import sys
import os, requests
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from custom_lib.automail_ai_craft import LinkedinWrapper, enrich_person_more
from custom_lib.automail_ai_search_v2 import search_people
from custom_lib.cookies_extractor_async import cookie_extractor_from_json
from dotenv import load_dotenv
import json
import os
load_dotenv()
import asyncio

import time

# Get cookies =========================================================================
url = 'http://localhost:3000/chat/api/playwright-local'
# url_main = 'http://trylisa.vercel.app/chat/api/playwright'

res = requests.get(
        url +
        f'?email={os.getenv("LINKEDIN_USER_OG")}&password={os.getenv("LINKEDIN_PASS_OG")}',
    )

json_data = res.json()
with open('multi_cookies/cookies_OG.json', 'w') as f:
    json.dump(json_data['cookies'], f, indent=4)

# Test search =========================================================================
# with open('multi_cookies/cookies_B3.json', 'r') as f:
#     cookies_1 = json.load(f)

# linkedin = LinkedinWrapper(username=os.getenv("LINKEDIN_USER_2"), password=os.getenv("LINKEDIN_PASS_2"), cookies=cookie_extractor_from_json(cookies_1))

# res = linkedin.search_people(
#     keywords="investment banking",
#     limit=10,
#     offset=0
# )
# print(res)
# Try double cookies =========================================================================
# dummy_username = 'dummy'
# dummy_password = 'dummy'

# with open('multi_cookies/cookies_1.json', 'r') as f:
#     cookies_1 = json.load(f)

# with open('multi_cookies/cookies_2.json', 'r') as f:
#     cookies_2 = json.load(f)

# with open('multi_cookies/cookies_3.json', 'r') as f:
#     cookies_3 = json.load(f)

# with open('multi_cookies/cookies_4.json', 'r') as f:
#     cookies_4 = json.load(f)

# with open('multi_cookies/public_ids.json', 'r') as f:
#     public_ids_json = json.load(f)

# def create_linkedin_wrapper(cookies):
#     return LinkedinWrapper(username=dummy_username, password=dummy_password, cookies=cookie_extractor_from_json(cookies))

# def create_search_coroutine(linkedin_wrapper: LinkedinWrapper, public_id: str):
#     async def search():
#         return linkedin_wrapper.get_profile(public_id=public_id)
#     return search

# async def search_concurrent(cookies_list, public_ids):
#     # Create LinkedIn wrappers for each set of cookies
#     linkedin_wrappers = [create_linkedin_wrapper(cookies) for cookies in cookies_list]
    
#     # Create and gather all search coroutines
#     coroutines = [create_search_coroutine(wrapper, public_id)() for wrapper, public_id in zip(linkedin_wrappers, public_ids)]
#     results = await asyncio.gather(*coroutines)
    
#     # Save results to a JSON file
#     with open('multi_cookies/result_fullprofiles.json', 'w') as f:
#         json.dump(results, f, indent=4)
    
#     return results

# # Example usage
# cookies_list = [cookies_1, cookies_2, cookies_3, cookies_4]  # Add more cookies as needed
# public_ids = public_ids_json[:4]  # Add more public IDs as needed
# asyncio.run(search_concurrent(cookies_list, public_ids))

# Extraction =========================================================================
# with open('multi_cookies/result_1.json', 'r') as f:
#     results = json.load(f)

# li = []
# for result in results:
#     public_id = result['url'].split('in/')[1].split('?')[0]
#     li.append(public_id)

# with open('multi_cookies/public_ids.json', 'w') as f:
#     json.dump(li, f, indent=4)


