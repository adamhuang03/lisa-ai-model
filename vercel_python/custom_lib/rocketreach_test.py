from ast import Tuple
import json
import requests
from bs4 import BeautifulSoup
from linkedin_api.linkedin import default_evade 
import random
import time
import logging

logger = logging.getLogger(__name__)

USER_AGENTS = [
    # Chrome on Windows 10
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    },
    # Firefox on Windows 10
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
            "Gecko/20100101 Firefox/121.0"
        )
    },
    # Edge on Windows 10
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Edge/120.0.0.0 Safari/537.36"
        )
    },
    # Safari on macOS
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.1 Safari/605.1.15"
        )
    },
    # Opera on Windows 10
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "OPR/106.0.0.0 Safari/537.36"
        )
    }
]

def get_random_headers():
    return random.choice(USER_AGENTS)

def structure_rocketreach_query(input: str):
    # Fetch the page content
    return f"site:rocketreach.co {input} email format"

def get_first_google_result_link(query):
    headers = get_random_headers()
    search_url = "https://www.bing.com/search"
    params = {"q": query, "num": "10"}
    # print(query)

    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code} from Google.")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    # with open('google_search_results.txt', 'w', encoding='utf-8') as f:
    #     f.write(soup.prettify())

    # Find RocketReach links in Bing search results
    link_tags = soup.select('a[href*="https://rocketreach.co"]')
    logger.info(f"Found {len(link_tags)} RocketReach links")
    
    if not link_tags:
        logger.error("No RocketReach links found in search results")
        return None
        
    # Get the first valid RocketReach link
    for link in link_tags:
        href = link.get('href')
        if href and 'rocketreach.co' in href and 'email-format' in href:
            return href
            
    return None


    # # Save the search results as a clean JSON
    # with open('google_search_results.html', 'w') as f:
    #     f.write(soup.prettify())


    # # First find the search container
    # search_div = soup.find('div', id='search')
    # if not search_div:
    #     print("No search results container found.")
    #     return None

    # # Inside it, find the first 'div.yuRUbf > a'
    # link_tag = search_div.select_one('div.yuRUbf > a')
    # if link_tag and link_tag.has_attr('href'):
    #     return link_tag['href']

    # print("No link found in the search results.")
    

def get_top_email_format(url):
    # Fetch the page content
    default_evade()
    headers = get_random_headers()
    headers_firefox = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) "
            "Gecko/20100101 Firefox/120.0"
        )
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }
    response = requests.get(url, headers=headers_firefox)
    # print(response.status_code, response.headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Locate the table containing the email formats
    # According to the provided HTML, the table is inside a div with class 'table-wpr'
    # We'll find the first table row after the thead, which should represent the most common pattern.
    table_wpr = soup.find('div', class_='table-wpr')
    if not table_wpr:
        return None

    # Find the first row inside the table body
    table = table_wpr.find('table', class_='table')
    if not table:
        return None
    
    tbody = table.find('tbody')
    if not tbody:
        return None
    
    first_row = tbody.find('tr')
    if not first_row:
        return None

    # Extract pattern and example from the first row
    cells = first_row.find_all('td')
    if len(cells) < 2:
        return None
    
    pattern = cells[0].get_text(strip=True)
    example = cells[1].get_text(strip=True)
    
    return pattern, example

import os, asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

SYSTEM_PROMPT = """You are an email format expert. Your task is to generate email addresses based on a person's name and a given email pattern format.
Follow these rules strictly:
1. Use ONLY the provided pattern format
2. Convert all output to lowercase
3. Remove any spaces or special characters unless specified in the pattern
4. If first name or last name is not complete (e.g., "Nathan B."), use "verifying"
5. Return ONLY a valid JSON array of email addresses in the exact same order as input names

IMPORTANT: Your entire response must be a single valid JSON array of strings.
Do not include any explanations, headers, or additional text.

Example input 1:
Names: ["Nathan Beber", "John Smith"]
Pattern: [first_initial][last]

Example response 1:
["nbeber", "jsmith"]

Example input 2:
Names: ["Nathan Beber", "John Smith", "Jane D."]
Pattern: [first].[last]

Example response 2:
["nathan.beber", "john.smith", "verifying"]"""

async def generate_email_gpt_batch(openai_client: AsyncOpenAI, names: list[str], pattern_info: str, batch_size: int = 10) -> list[str]:
    """
    Generate email addresses in batches using GPT-3.5 Turbo.
    
    Args:
        openai_client: An instance of the OpenAI client
        names: List of full names to process
        pattern_info: String containing pattern and example (e.g., "[first].[last]@company.com")
        batch_size: Size of each batch (default: 10)
        
    Returns:
        List of generated email addresses in same order as input names
        
    Example:
        >>> names = ["Nathan Beber", "John Smith", "Jane Doe"]
        >>> pattern = '''Top Email Format Pattern: [first_initial][last]
        ... Example: jdoe@fb.com'''
        >>> await generate_email_gpt_batch(names, pattern)
        ['nbeber@fb.com', 'jsmith@fb.com', 'jdoe@fb.com']
    """
    all_emails = []
    
    # Process names in batches
    for i in range(0, len(names), batch_size):
        batch = names[i:i + batch_size]
        
        try:
            # Create a single prompt for the entire batch
            batch_prompt = "\n".join([f"Name {j+1}: {name}" for j, name in enumerate(batch)])
            
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"""
                Email Format Pattern:
                {pattern_info}

                Names to process:
                {batch_prompt}

                Generate email addresses for all names using the above pattern format.
                Return ONLY the email addresses, one per line, in the exact same order as the input names.
                """}
            ]

            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0,
                max_tokens=100
            )
            try:
                emails = json.loads(response.choices[0].message.content)
            except Exception as e:
                print(f"Error json formatting batch {i//batch_size + 1}: {str(e)}")
                # Add None for each failed email in this batch
                emails = [None] * len(batch)
            
            all_emails.extend(emails)
            
        except Exception as e:
            print(f"Error processing batch {i//batch_size + 1}: {str(e)}")
            # Add None for each failed email in this batch
            all_emails.extend([None] * len(batch))
    
    return all_emails

async def generate_email_gpt(name: str, pattern_info: str):
    """Single email generation (wrapper around batch function)"""
    results = await generate_email_gpt_batch([name], pattern_info)
    return results[0] if results else None

async def search_and_generate_emails(async_openai_client: AsyncOpenAI, company: str, names: list[str]):
    """
    Search for the company's top email format pattern and generate emails
    """
    query = structure_rocketreach_query(company)
    first_link = get_first_google_result_link(query)
    if first_link:
        print("First link found:", first_link)
        result = get_top_email_format(first_link)
        if result:
            pattern, example = result
            print(f"For URL: {first_link}")
            print(f"Top Email Format Pattern: {pattern}")
            print(f"Example: {example}")
            print("-" * 50)

            email_domain = example.split("@")[1]
            print(f"Email Domain: {email_domain}")

            emails = await generate_email_gpt_batch(async_openai_client, names, pattern)
            emails_appended = [f"{email}@{email_domain}" for email in emails]
            print(f"Generated Emails: {emails_appended}")

            return [(first_link, pattern, example), emails_appended]
        else:
            print("Could not find format for", first_link)
    else:
        print("No link found.")

if __name__ == "__main__":
    # Example search
    input_companies = [
        # "Moelis",
        # "Morgan Stanley",
        # "GitHub",
        # "Google",
        # "Microsoft",
        # "Apple",
        # "Facebook",
        "Twitter",
        # "Amazon",
        # "Tesla",
        # "Netflix",
        # "Spotify",
        # "Airbnb",
        # "Uber",
        # "Lyft",
        # "Snapchat",
        # "Instagram",
        # "TikTok",
        # "Pinterest",
        # "Reddit",
    ]
    names = [
                    "Nathan Beber", 
                    "John Smith", 
                    "Jane Doe",
                    "Abdullah Chandna",
                    "Hasan Raza",
                    "Ahmed Ali",
                    "Nathan Beber",
                    "John Smith",
                    "Jane Doe",
                    "Abdullah Chandna"
                ]
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    for company in input_companies:
        asyncio.run(search_and_generate_emails(client, company, names))

# if __name__ == "__main__":
#     # Example search
#     input_companies = [
#         # "Moelis",
#         # "Morgan Stanley",
#         # "GitHub",
#         # "Google",
#         # "Microsoft",
#         # "Apple",
#         # "Facebook",
#         "Twitter",
#         # "Amazon",
#         # "Tesla",
#         # "Netflix",
#         # "Spotify",
#         # "Airbnb",
#         # "Uber",
#         # "Lyft",
#         # "Snapchat",
#         # "Instagram",
#         # "TikTok",
#         # "Pinterest",
#         # "Reddit",
#     ]
#     client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
#     for company in input_companies:
#         query = structure_rocketreach_query(company)
#         first_link = get_first_google_result_link(query)
#         if first_link:
#             print("First link found:", first_link)
#             result = get_top_email_format(first_link)
#             if result:
#                 pattern, example = result
#                 print(f"For URL: {first_link}")
#                 print(f"Top Email Format Pattern: {pattern}")
#                 print(f"Example: {example}")
#                 print("-" * 50)

#                 email_domain = example.split("@")[1]
#                 print(f"Email Domain: {email_domain}")

#                 # Generate emails using GPT-3.5 Turbo
#                 names = [
#                     "Nathan Beber", 
#                     "John Smith", 
#                     "Jane Doe",
#                     "Abdullah Chandna",
#                     "Hasan Raza",
#                     "Ahmed Ali",
#                     "Nathan Beber",
#                     "John Smith",
#                     "Jane Doe",
#                     "Abdullah Chandna"
#                 ]
#                 emails = asyncio.run(generate_email_gpt_batch(client, names, pattern))
#                 emails_appended = [f"{email}@{email_domain}" for email in emails]
#                 print(f"Generated Emails: {emails_appended}")
#             else:
#                 print("Could not find format for", first_link)
#         else:
#             print("No link found.")
    
    # urls = [
    #     "https://rocketreach.co/moelis-company-email-format_b5c01de7f42e0fcd",
    #     "https://rocketreach.co/morgan-stanley-email-format_b5c18cabf42e08c4",
    #     "https://rocketreach.co/github-email-format_b5d3bf8bf42e46c1"
    # ]

    # for url in urls:
    #     result = get_top_email_format(url)
    #     if result:
    #         pattern, example = result
    #         print(f"For URL: {url}")
    #         print(f"Top Email Format Pattern: {pattern}")
    #         print(f"Example: {example}")
    #         print("-" * 50)

    #         # Generate emails using GPT-3.5 Turbo
    #         names = ["Nathan Beber", "John Smith", "Jane Doe"]
    #         emails = asyncio.run(generate_email_gpt_batch(names, pattern))
    #         print(f"Generated Emails: {emails}")
    #     else:
    #         print(f"Could not find format for {url}")
