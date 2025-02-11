# import sys, os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from custom_lib.cookies_extractor_async import cookie_extractor_from_json
# from custom_lib.automail_ai_craft import LinkedinWrapper, enrich_person_more
# from custom_lib.automail_ai_search_v2 import search_people
# from dotenv import load_dotenv
# import json

# load_dotenv()

# with open('multi_cookies/cookies_A1.json', 'r') as f:
#     cookies_C5 = json.load(f)
# cookies_jar = cookie_extractor_from_json(cookies_C5)
# linkedin = LinkedinWrapper(os.getenv("LINKEDIN_USER_1"), os.getenv("LINKEDIN_PASS_1"), cookies=cookies_jar, debug=True)

# # grab the list of poeple
# def get_company_id(input: str) -> dict:
#     search_results = linkedin.search_companies(
#             keywords=[input],
#             limit=10,
#             offset=0
#         )        
#     # Use the first result's URN ID
#     company_id = search_results[0]["urn_id"]
#     company_found_name = search_results[0]["name"]

#     return {"company_id": company_id, "company_found_name": company_found_name}


# with open("quick_ask_jeff/company_list/list4.json", "r") as f:
#     companies = json.load(f)

# companies_ids = []

# for company in companies:
#     print(f"Getting company id for {company}")
#     try:
#         company_id = get_company_id(company)
#         companies_ids.append(company_id)
#     except Exception as e:
#         companies_ids.append({"company": company, "error": str(e)})
#         print(f"Error for company {company}: {e}")
#         continue

# with open("quick_ask_jeff/company_list/companies_ids_4.json", "w") as f:
#     json.dump(companies_ids, f, indent=4)


# NEXT PART ==================================================================

import urllib.parse
import json

with open("quick_ask_jeff/company_list/companies_ids_1.json", "r") as f:
    companies_ids_1 = json.load(f)

with open("quick_ask_jeff/company_list/companies_ids_2.json", "r") as f:
    companies_ids_2 = json.load(f)

with open("quick_ask_jeff/company_list/companies_ids_3.json", "r") as f:
    companies_ids_3 = json.load(f)

with open("quick_ask_jeff/company_list/companies_ids_4.json", "r") as f:
    companies_ids_4 = json.load(f)

companies_ids = companies_ids_1 + companies_ids_2 + companies_ids_3 + companies_ids_4

companies_ids = [company_set['company_id'] if 'company_id' in company_set else None for company_set in companies_ids]

companies_ids = list(set(companies_ids))

ids = companies_ids
encoded_companies = urllib.parse.quote(json.dumps(ids))

main_str = "https://www.linkedin.com/search/results/people/?currentCompany={}&keywords=data&origin=FACETED_SEARCH&sid=mSj".format(encoded_companies)
# %5B%22100025096%22%2C%22105149290%22%2C%2290009551%22%5D
tor_str = "https://www.linkedin.com/search/results/people/?currentCompany={}&geoUrn=GEO&keywords=KEY&origin=FACETED_SEARCH&sid=mSj&titleFreeText=TITLE"

for i in range(0, len(companies_ids), 10):
    print(tor_str.format(urllib.parse.quote(json.dumps(companies_ids[i:i+10]))))