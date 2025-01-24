import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from custom_lib.automail_ai_craft import LinkedinWrapper, enrich_person_more
from custom_lib.automail_ai_search_v2 import search_people
from dotenv import load_dotenv
import json

load_dotenv()

linkedin = LinkedinWrapper(os.getenv("LINKEDIN_USER"), os.getenv("LINKEDIN_PASS"), debug=True)

# result = enrich_person_more(
#         linkedin=linkedin,
#         value="https://www.linkedin.com/in/ryan-hui-cfa-323a6529/",
#         url_value=True
#     )

result = linkedin.search_people(
    keywords="investment banking",
    limit=10,
    offset=0
)

# result = linkedin.add_connection(
#     profile_public_id="hasan-raza-",
#     message="Hello, this is a test message",
# )

print(json.dumps(result, indent=4))