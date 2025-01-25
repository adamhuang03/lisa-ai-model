from typing import List, Tuple, Optional
from custom_lib.linkedin_wrapper import LinkedinWrapper
import logging
import json
import os
from openai import OpenAI
import asyncio


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from prompt.email import EMAIL_SYSTEM_PROMPT, EMAIL_TEMPLATE

# function to enrich each person in a json, toggle for urn_id or url
def enrich_person(
    linkedin: LinkedinWrapper,
    value: str,
    url_value: bool = False
) -> dict:
    logger.info("Starting profile enrichment for value: %s (url_value=%s)", value, url_value)
    
    # Create a cleaned person dictionary with relevant fields
    if url_value:
        url = value.split('?')[0].rstrip('/')
        id = url.split('/')[-1]
        logger.info("Extracting profile using public_id: %s", id)
    else:
        id = value
        logger.info("Extracting profile using urn_id: %s", value)
    
    person = linkedin.get_profile(id)
    if not person:
        logger.warning("No profile data returned for value: %s", value)
        return {}
    
    logger.info("Successfully retrieved profile for %s %s", 
                person.get("firstName", "Unknown"), 
                person.get("lastName", "Unknown"))
    
    cleaned_person = {
        "personal": {
            "first_name": person.get("firstName"),
            "last_name": person.get("lastName"),
            "headline": person.get("headline"),
            "location": person.get("locationName"),
            "city": person.get("geoLocationName"),
            "industry": person.get("industryName")
        },
        "experiences": [],
        "education": []
    }
    
    # Add experiences
    experience_count = len(person.get("experience", []))
    logger.info("Processing %d experiences", experience_count)
    for exp in person.get("experience", []):
        cleaned_exp = {
            "title": exp.get("title"),
            "company": exp.get("companyName"),
            "description": exp.get("description"),
            "start_date": exp.get("startDate"),
            "end_date": exp.get("endDate")
        }
        cleaned_person["experiences"].append(cleaned_exp)
    
    def get_urn_from_school_urn_list(raw_string: str) -> str:
        """
        Return the URN of a raw group update

        Example: urn:li:fs_miniProfile:<id>
        Example: urn:li:fs_updateV2:(<urn>,GROUP_FEED,EMPTY,DEFAULT,false)
        """
        string = raw_string.split("(")[1].split(",")[1]
        return string[:len(string)-1]
    
    # Add education
    education_count = len(person.get("education", []))
    logger.info("Processing %d education entries", education_count)
    for edu in person.get("education", []):
        cleaned_edu = {
            "school_urn_id": get_urn_from_school_urn_list(edu.get("entityUrn")),
            "school": edu.get("schoolName"),
            "activities": edu.get("activities"),
            "grade": edu.get("grade"),
            "start_date": edu.get("timePeriod", {}).get("startDate"),
            "end_date": edu.get("timePeriod", {}).get("endDate")
        }
        cleaned_person["education"].append(cleaned_edu)
    
    # Add identifier based on parameter
    if url_value:
        cleaned_person["id"] = person.get("public_id")
        logger.info("Added public_id to profile")
    else:
        cleaned_person["id"] = person.get("profile_urn")
        logger.info("Added profile_urn to profile")
    
    logger.info("Successfully enriched profile data")
    return cleaned_person

def multi_enrich_persons(
    linkedin: LinkedinWrapper,
    values: List[str],
    url_value: bool = False
) -> List[dict]:
    return [enrich_person(linkedin, value, url_value) for value in values]

async def draft_emails_batch(
    openai: OpenAI,
    user_profile: dict,
    candidate_profiles: List[dict],
    keyword_industry: str,
    email_template: str,
    batch_size: int = 5
) -> List[str]:
    async def process_batch(batch):
        tasks = []
        for candidate_profile in batch:
            messages = [
                {"role": "system", "content": EMAIL_SYSTEM_PROMPT},
                {"role": "user", "content": f"""
                        User Profile:
                {json.dumps(user_profile, indent=2)}

                Candidate Profile:
                {json.dumps(candidate_profile, indent=2)}

                Num: 1
                Role: {keyword_industry}
                Email template:
                {email_template}
                """}
            ]
            
            tasks.append(
                openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
                )
            )
        
        responses = await asyncio.gather(*tasks)
        return [response.choices[0].message.content for response in responses]

    all_emails = []
    for i in range(0, len(candidate_profiles), batch_size):
        batch = candidate_profiles[i:i + batch_size]
        emails = await process_batch(batch)
        all_emails.extend(emails)
    
    return all_emails

def draft_email(
    openai: OpenAI,
    user_profile: dict,
    candidate_profile: dict,
    keyword_industry: str,
    email_template: str
) -> str:
    messages = [
        {"role": "system", "content": EMAIL_SYSTEM_PROMPT},
        {"role": "user", "content": f"""
                User Profile:
        {json.dumps(user_profile, indent=2)}

        Candidate Profile:
        {json.dumps(candidate_profile, indent=2)}

        Num: 1
        Role: {keyword_industry}
        Email template:
        {email_template}
        """}
    ]
    
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=500
    )

    return response.choices[0].message.content  

def enrich_person_more(
    linkedin: LinkedinWrapper,
    value: str,
    url_value: bool = False
) -> dict:
    logger.info("Starting profile enrichment for value: %s (url_value=%s)", value, url_value)
    
    # Create a cleaned person dictionary with relevant fields
    if url_value:
        url = value.split('?')[0].rstrip('/')
        id = url.split('/')[-1]
        logger.info("Extracting profile using public_id: %s", id)
    else:
        id = value
        logger.info("Extracting profile using urn_id: %s", value)
    
    person = linkedin.get_profile(id)

    if not person:
        logger.warning("No profile data returned for value: %s", value)
        return {}
    
    logger.info("Successfully retrieved profile for %s %s", 
                person.get("firstName", "Unknown"), 
                person.get("lastName", "Unknown"))
    
    cleaned_person = {
        "personal": {
            "first_name": person.get("firstName"),
            "last_name": person.get("lastName"),
            "headline": person.get("headline"),
            "location": person.get("locationName"),
            "city": person.get("geoLocationName"),
            "industry": person.get("industryName")
        },
        "experiences": [],
        "education": [],
        "skills": [skill['name'] for skill in person.get("skills", [])]
    }
    
    # Add experiences
    experience_count = len(person.get("experience", []))
    logger.info("Processing %d experiences", experience_count)
    for exp in person.get("experience", []):
        cleaned_exp = {
            "title": exp.get("title"),
            "company": exp.get("companyName"),
            "company_public_id": exp.get("companyPublicId"),
            "description": exp.get("description"),
            "start_date": exp.get("startDate"),
            "end_date": exp.get("endDate")
        }
        cleaned_person["experiences"].append(cleaned_exp)
    
    # Add education
    education_count = len(person.get("education", []))
    logger.info("Processing %d education entries", education_count)
    for edu in person.get("education", []):
        cleaned_edu = {
            "school": edu.get("schoolName"),
            "activities": edu.get("activities"),
            "grade": edu.get("grade"),
            "start_date": edu.get("timePeriod", {}).get("startDate"),
            "end_date": edu.get("timePeriod", {}).get("endDate")
        }
        cleaned_person["education"].append(cleaned_edu)
    
    # Add identifier based on parameter
    if url_value:
        cleaned_person["id"] = person.get("public_id")
        logger.info("Added public_id to profile")
    else:
        cleaned_person["id"] = person.get("profile_urn")
        logger.info("Added profile_urn to profile")
    
    logger.info("Successfully enriched profile data")
    return cleaned_person


if __name__ == "__main__":

    import json, os
    from pprint import pprint

    from dotenv import load_dotenv
    load_dotenv()
    openai = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )
    linkedin_user = os.getenv("LINKEDIN_USER")
    linkedin_password = os.getenv("LINKEDIN_PASSWORD")
    linkedin = LinkedinWrapper(linkedin_user, linkedin_password, debug=True)

    # ==================================================================
    # Single enrichement

    # result = enrich_person(
    #     linkedin=linkedin,
    #     value="https://www.linkedin.com/in/rachel-levitt-bb0922b5/",
    #     url_value=True
    # )

    # with open("data/user_profile_vaishika.json", "w") as f:
    #     import json
    #     json.dump(result, f, indent=4)

    # with open("data/user_profile_hasan.json", "r") as f:
    #     user_profile = json.load(f)
    
    # email = draft_email(
    #     openai=openai,
    #     user_profile=user_profile,
    #     candidate_profile=result
    # )

    # print("\nGenerated Email:")
    # print(email)
    
    # ==================================================================
    # Multi enrichement

    # Read csv
    # csv_file = "v2_output/linkedin_data.csv"
    # with open(csv_file, "r") as f:
    #     csv_data = [line.strip().split(",") for line in f.readlines()]
    # # Get the 1st column
    # list_of_urns = [row[0] for row in csv_data]
    
    # multi_result_enriched = multi_enrich_persons(
    #     linkedin=linkedin,
    #     values=list_of_urns,
    #     url_value=False
    # )

    # with open("data/user_profile_vaishika.json", "r") as f:
    #     user_profile = json.load(f)

    # with open("v2_search/params.json", "r") as f:
    #     params = json.load(f)
    #     keyword_industry = params["keyword_industry"]

    # emails = asyncio.run(draft_emails_batch(
    #     openai=openai,
    #     user_profile=user_profile,
    #     candidate_profiles=multi_result_enriched,
    #     keyword_industry=keyword_industry,
    #     email_template=EMAIL_TEMPLATE
    # ))

    # # Add the enriched data to the csv data
    # for i in range(len(csv_data)):
    #     csv_data[i].append(json.dumps(emails[i]))
    
    # # Save the csv data
    # with open("v2_output/linkedin_data_w_enriched.csv", "w") as f:
    #     f.write("urn_id,url,email\n")
    #     f.write("\n".join([",".join(row) for row in csv_data]))

    # ==================================================================

    result = enrich_person(
        linkedin=linkedin,
        value="https://www.linkedin.com/in/rachel-levitt-bb0922b5/",
        url_value=True
    )
    with open("user_profile_rachel.json", "w") as f:
        import json
        json.dump(result, f, indent=4)

    # print(json.dumps(result, indent=4))

    # ==================================================================

    

