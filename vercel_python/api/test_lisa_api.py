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

import time

url = 'http://localhost:3000/chat/api/playwright'
url_main = 'http://trylisa.vercel.app/chat/api/playwright'

# res = requests.get(
#         url +
#         f'?email={os.getenv("LINKEDIN_USER_OG")}&password={os.getenv("LINKEDIN_PASS_OG")}',
#     )

# json_data = res.json()
# print(json.dumps(json_data['cookies'], indent=4))

json_data_cookies = [
    {
        "name": "lang",
        "value": "v=2&lang=en-us",
        "domain": ".linkedin.com",
        "path": "/",
        "expires": -1,
        "httpOnly": False,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "JSESSIONID",
        "value": "\"ajax:2119392652497546283\"",
        "domain": ".www.linkedin.com",
        "path": "/",
        "expires": 1745209533.51162,
        "httpOnly": False,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "bcookie",
        "value": "\"v=2&9225dfab-d0db-4a00-84af-8385823e1f94\"",
        "domain": ".linkedin.com",
        "path": "/",
        "expires": 1768969533.511639,
        "httpOnly": False,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "bscookie",
        "value": "\"v=1&20250121042511aec0d440-9d0c-4441-8899-caa0d67b3996AQFyR5os-LI3x2ab2oKofjRrls48khnm\"",
        "domain": ".www.linkedin.com",
        "path": "/",
        "expires": 1768969533.511674,
        "httpOnly": True,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "li_gc",
        "value": "MTswOzE3Mzc0MzM1MTE7MjswMjFoWsYlfx5gZlpP1CZtgi8S/GeFayth3s4ccHuJ31wfOg==",
        "domain": ".linkedin.com",
        "path": "/",
        "expires": 1752985512.008158,
        "httpOnly": False,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "__cf_bm",
        "value": "SFP8dDSI5UjQj61MIEHPbdqpBnvk6ene8n8s8dbeUvI-1737433511-1.0.1.1-va_FPplvKzEL3mAKPHs0jktvX3uRw3iQzlmSXooZ2i7fYx4mVJLW0OLJbd.l0eHRKejcPPjhQPOEVKEAz1B8Zw",
        "domain": ".linkedin.com",
        "path": "/",
        "expires": 1737435312.008199,
        "httpOnly": True,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "NID",
        "value": "520=etWlk17ceDYaN32XiTMGRgHPnT6H_Fs1UemkzH07ryiWTglBbQ1zzLWysnbHAIXueGAMEcA_GlnNZENdMHB-oSWDgLcP9T1NQYL0adS8m-IgaT3JMd7iH-CIz2oTsovjxtR54o1Il8eEVc3qZRr61LPKK3QBTkGxb2wlLFrVz3Ie_2YJLiGkSo7rXkLC",
        "domain": ".google.com",
        "path": "/",
        "expires": 1753244728.519726,
        "httpOnly": True,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "li_rm",
        "value": "AQG6ICCYHqEs2wAAAZSHG8temmpbPBPRaan9Lbb1lsknsi-3En32XxbAHwhkIOW8CX34nXM_ulg3fCO0t4PLfKeVzFd4VrkUiiXJaICe9VAdLYC9f41cVVcgfz-sMbDRqxg5dpS7dEW-GZSmBRqRH0mZnbMZxcvHdMN7xaqP92NdU38Z_SNgsRkRecQFfzOF59-TvlBNs6oCLI-Zw6AZJ6rYkbOgIWR0s1B6GPkitrBMbvpd8u_wLgrIENVhWJJRTrf_2OYUdjew8SoVVnYtIbB8Vq8xoDYBb8kjFj_wAj8M14MgKfSSd_mwrfHO-RUiT5aZ7W9mnI3GrKRLicc",
        "domain": ".www.linkedin.com",
        "path": "/",
        "expires": 1768969533.51143,
        "httpOnly": True,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "li_at",
        "value": "AQEDAVXBBWsB2s58AAABlIcbyygAAAGUqyhPKE4Acay0UZdMYgish8ZZrCQdMaucjL4uDfwGxiMxbrlL5IJmrOq_0X6-woee9TeM5r5IjxQaVGIU5CxGd9z6dt-1Gq9NUPXvEhk9na9DA_ObBAmQCb6O",
        "domain": ".www.linkedin.com",
        "path": "/",
        "expires": 1768969533.511576,
        "httpOnly": True,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "liap",
        "value": "true",
        "domain": ".linkedin.com",
        "path": "/",
        "expires": 1745209533.511609,
        "httpOnly": False,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "li_mc",
        "value": "MTswOzE3Mzc0MzM1MzM7MjswMjGmLBygHEOx6yRdQYIrOabpseYaX/snv4qWknrQWzpWRA==",
        "domain": ".linkedin.com",
        "path": "/",
        "expires": 1752985533.979866,
        "httpOnly": False,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "lidc",
        "value": "\"b=TB95:s=T:r=T:a=T:p=T:g=4371:u=9:x=1:i=1737433533:t=1737519437:v=2:sig=AQH8JsdzaIUb3dj1Wce5MHYqzU5Trs_Z\"",
        "domain": ".linkedin.com",
        "path": "/",
        "expires": 1737519437.97997,
        "httpOnly": False,
        "secure": True,
        "sameSite": "None"
    }
]

json_data = {}
if 'error' in json_data:
    print(False)
else:
    print(True)
    cookies_jar = cookie_extractor_from_json(json_data_cookies)
    linkedin = LinkedinWrapper(os.getenv("LINKEDIN_USER"), os.getenv("LINKEDIN_PASS"), cookies=cookies_jar, debug=True)

    result = linkedin.search_people(
        keywords="investment banking",
        limit=10,
        offset=0
    )
    print(json.dumps(result, indent=4))

    # result = linkedin.add_connection(
    #     profile_public_id="hasan-raza-",
    #     message="Hello, this is a test message",
    # )
    # print(result)

    # wait 10 mins, send to adamshuang + ethanfeilungchen

    # result = linkedin.add_connection(
    #     profile_public_id="ethanfeilungchen",
    #     message="Hello, this is a test message",
    # )
    # print(result)

    # tomorrow moring, run a search for "investment banking" to see if [], if not then it means the proxy allows mutliple locations to be active ip's at once with multiple cookies, so we can keep refreshing
    # if I sign out of my toronto linkedin, the brazil one will stille work