import sys
import os
import logging
logger = logging.getLogger(__name__)

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_lib.automail_ai_search_v2 import *
from custom_lib.automail_ai_craft import *
from custom_lib.linkedin_wrapper import *
from openai import AsyncOpenAI, OpenAI

if __name__ == "__main__":

    import json
    from pprint import pprint

    from dotenv import load_dotenv
    load_dotenv()
    openai = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )
    openai_async = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )
    linkedin_user = os.getenv("LINKEDIN_USER")
    linkedin_password = os.getenv("LINKEDIN_PASSWORD")
    linkedin = LinkedinWrapper(linkedin_user, linkedin_password, debug=True)

    # =============================== 10 profile test
    # linkedin profile into a format that can be searchable
    
    # enrich company of linkedin profile
    # with open(os.path.join(os.path.dirname(__file__), 'enriched_linkedin_profile_1.json')) as f:
    #     linkedin_profile = json.load(f)

    # experiences = linkedin_profile.get('experiences')
    # used_company_dict = {}
    # used_company_ids = set()
    # for exp in experiences:
    #     company_public_id = exp.get('company_public_id')
    #     if company_public_id in used_company_ids:
    #         # no need to re add the enrichement, going to waste openai tokens
    #         continue
        
    #     # where NextJS will call the API
    #     company = linkedin.get_company(company_public_id)
        
    #     enriched_company = {
    #         'company_details': {
    #             'description': company.get('description'),
    #             'staffCountRange': company.get('staffCountRange')
    #         }
    #     }
    #     used_company_dict[company_public_id] = enriched_company
    #     exp.update(enriched_company)
    #     used_company_ids.add(company_public_id)

    # linkedin_profile.update({'experiences': experiences})

    # with open(os.path.join(os.path.dirname(__file__), 'enriched_linkedin_profile_2.json'), 'w') as f:
    #     json.dump(linkedin_profile, f, indent=4)


    # ===============================================================================
    # run search for 10 profiles

    # with open(os.path.join(os.path.dirname(__file__), 'diction.json'), 'r') as f:
    #     diction = json.load(f)

    # def get_company_id(linkedin, company_name):
    #     search_results = linkedin.search_companies(
    #         keywords=[company_name],
    #         limit=10,
    #         offset=0
    #     )        
    #     # Use the first result's URN ID
    #     company_id = search_results[0]["urn_id"]
    #     company_found_name = search_results[0]["name"]

    #     return (company_id, company_found_name)

    # search = []
    # keywords = diction.get('linkedinSearch').get('keywords')
    # pastCompanies = diction.get('linkedinSearch').get('pastCompanies')
    # for pastCompany in pastCompanies:
    #     pastCompany = get_company_id(linkedin, pastCompany)
    #     print(pastCompany)
    # updated_pastCompanies = ['5020707', '1382', '978774', '1826', '1800', '1067', '2589', '3537', '1426']

    # output = []
    # for keyword in keywords:
    #     results = linkedin.search_people(
    #         keywords=keyword,
    #         past_companies=updated_pastCompanies,
    #         or_past_companies=True,
    #         limit=10,
    #         offset=0
    #     )
    #     output.extend(results)


    # with open(os.path.join(os.path.dirname(__file__), 'results.json'), 'w') as f:
    #     json.dump(output, f, indent=4)

    # ===============================================================================
    # enrich 10 profiles companies
    # with open(os.path.join(os.path.dirname(__file__), 'results.json'), 'r') as f:
    #     results = json.load(f)

    # output = []
    # for result in results:
    #     result = enrich_person_more(
    #         linkedin=linkedin,
    #         value=result.get('url'),
    #         url_value=True
    #     )
    #     output.append(result)

    # with open(os.path.join(os.path.dirname(__file__), 'enriched_results.json'), 'w') as f:
    #     json.dump(output, f, indent=4)

    # enrich compaanies for those 10 profiles
    # with open(os.path.join(os.path.dirname(__file__), 'enriched_results.json'), 'r') as f:
    #     enriched_results = json.load(f)

    used_company_dict = {}
    for profile in enriched_results:
        experiences = profile.get('experiences')
        used_company_ids = set()
        for exp in experiences:
            company_public_id = exp.get('company_public_id')
            if company_public_id in used_company_ids:
                # no need to re add the enrichement, going to waste openai tokens
                logger.info("Company already enriched for public_id: %s", company_public_id)
                continue   
            # where NextJS will call the API
            if company_public_id in used_company_dict:
                exp.update(used_company_dict[company_public_id])
                logger.info("Reusing enrichement for public_id: %s", company_public_id)
                continue
            
            else: 
                logger.info("Searching LinkedIn for company: %s", company_public_id)
                try:
                    company = linkedin.get_company(company_public_id)
                except:
                    logger.warning("No profile data returned for value: %s", company_public_id)
                    continue
                
                enriched_company = {
                    'company_details': {
                        'description': company.get('description'),
                        'staffCountRange': company.get('staffCountRange')
                    }
                }
                used_company_dict[company_public_id] = enriched_company
                exp.update(enriched_company)
                used_company_ids.add(company_public_id)

        profile.update({'experiences': experiences})
    
    # with open(os.path.join(os.path.dirname(__file__), 'enriched_addedCompanyresults.json'), 'w') as f:
    #     json.dump(enriched_results, f, indent=4)

    # # ===============================================================================
    # compare profiles of these 10

    import asyncio
    from typing import Dict, Any
    import re

    with open(os.path.join(os.path.dirname(__file__), 'enriched_addedCompanyresults_test.json'), 'r') as f:
        enriched_results = json.load(f)
    
    with open(os.path.join(os.path.dirname(__file__), 'enriched_linkedin_profile_2.json'), 'r') as f:
        ideal_profile = json.load(f)

    def extract_relevant_profile_data(profile: Dict[Any, Any]) -> Dict[Any, Any]:
        """Extract only the relevant fields to reduce token usage."""
        return {
            "experiences": [{
                "title": exp.get("title"),
                "description": exp.get("description"),
                "company_details": exp.get("company_details"),
                "duration": exp.get("duration"),
                "location": exp.get("location")
            } for exp in profile.get("experiences", [])],
            "education": profile.get("education"),
            "skills": profile.get("skills")
        }

    ideal_profile_filtered = extract_relevant_profile_data(ideal_profile)

    async def process_profiles():
        tasks_1 = []
        tasks_2 = []
        for enriched_profile in enriched_results:
            profile_id = enriched_profile.get("id")
            name = ' '.join([enriched_profile.get("personal").get("first_name"), enriched_profile.get("personal").get("last_name")])
            headline = enriched_profile.get("personal").get("headline")
            city = enriched_profile.get("personal").get("city")
            
            print(profile_id)
            enriched_profile_filtered = extract_relevant_profile_data(enriched_profile)
            
            # messages = [
            #     {"role": "system", "content": """
            #     You are an intelligent assistant comparing two dictionaries of people profiles: a candidate's profile and an ideal profile. Focus on these criteria:
            #     - Experience Range: Compare total years of experience to the ideal profile experience range.
            #     - Company Background: Evaluate the types of companies (industry, size, reputation) of the candidate in relation to the ideal profile to determine relevance.
            #     - Job Roles Background: Compare relevant skill sets of the candidate based on role titles, role descriptions, and company descriptions to determine relevance to ideal profile.

            #     Elements of JSON:
            #     - score (experience range, company background, job roles) is an integer (0, 1, 2) denoting the overall similarity, with 0 being the least similar and 2 being the most similar.
            #     - description briefly explains the main factors contributing to the score, highlighting both strengths and gaps.

            #     Output a single JSON object with the structure:
            #     {
            #         "score_details": {
            #             "score_experience_range": int,
            #             "score_company_background": int,
            #             "score_job_roles": int,
            #             "description": "string"
            #         }
            #     }

            #     IMPORTANT: Do not respond to anything other than the JSON object.
            #     """
            #     },
            #     {"role": "user", "content": f"""
            #             ideal profile:
            #             {json.dumps(ideal_profile_filtered, indent=2)}

            #             candidate profile: 
            #             {json.dumps(enriched_profile_filtered, indent=2)}
            #             """
            #     }
            # ]

            ideal_experiences = ideal_profile_filtered.get('experiences')
            enriched_experiences = enriched_profile_filtered.get('experiences')

            messages_current_experience = [
                {"role": "system", "content": """
                You are an intelligent assistant comparing two dictionaries of subsections of linkedin people profiles: a candidate's profile and an ideal profile. Focus on this criteria: 
                - Combining the company_detail and the title, how similar is the candidate's skill set to the ideal profiles? 

                Elements of JSON:
                - score is an integer (0, 1, 2) denoting the overall similarity, wiith 0 being the least similar and 2 being the most similar. 
                - description briefly explains the main factors contributing to the score, highlighting both strengths and gaps.

                Output a single JSON object with the structure:
                {
                    "score_details": {
                        "score": int,
                        "description": "string"
                    }
                }

                IMPORTANT: Do not respond to anything other than the JSON object.
                """
                },
                {"role": "user", "content": f"""
                        ideal profile:
                        {json.dumps(ideal_experiences[0], indent=2)}

                        candidate profile: 
                        {json.dumps(enriched_experiences[0], indent=2)}
                        """
                }
            ]

            messages_past_experiences = [
                {"role": "system", "content": """
                You are an intelligent assistant comparing two dictionaries of subsections of linkedin people profiles: a candidate's profile and an ideal profile. Focus on this criteria: 
                - Combining multiple experiences' company_detail and the title, how similar is the candidate's skill set to the ideal profile's? Score can be high as long as the majority experiences are similar.

                Elements of JSON:
                - score is an integer (0, 1, 2) denoting the overall similarity, wiith 0 being the least similar and 2 being the most similar. 
                - description briefly explains the main factors contributing to the score, highlighting both strengths and gaps.

                Output a single JSON object with the structure:
                {
                    "score_details": {
                        "score": int,
                        "description": "string"
                    }
                }

                IMPORTANT: Do not respond to anything other than the JSON object.
                """
                },
                {"role": "user", "content": f"""
                        ideal profile:
                        {json.dumps(ideal_experiences[1:], indent=2)}

                        candidate profile: 
                        {json.dumps(enriched_experiences[1:], indent=2)}
                        """
                }
            ]
            
            tasks_1.append(
                (
                    profile_id,
                    openai_async.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages_current_experience,
                    temperature=0.7,
                    max_tokens=200
                    ),
                    {
                        "name": name,
                        "headline": headline,
                        "city": city
                    }
                )
            )
            tasks_2.append(
                (
                    profile_id,
                    openai_async.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages_past_experiences,
                    temperature=0.7,
                    max_tokens=200
                    )
                )
            )
        
        responses_1 = await asyncio.gather(*[task[1] for task in tasks_1])
        responses_1_clean = []
        for task, response_1 in zip(tasks_1, responses_1):
            try:
                # Remove code block markers and clean the JSON
                content = response_1.choices[0].message.content.strip()
                content = re.sub(r'^```json\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
                # Now extract just the JSON object
                content = re.sub(r'^.*?{', '{', content)
                content = re.sub(r'}.*$', '}', content)
                score_details = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON for {task[0]}: {str(e)}\nResponse content: {response_1.choices[0].message.content}")
                score_details = {}
                continue
            responses_1_clean.append({
                "profile_id": task[0], 
                "profile_details": task[2], 
                "score_current": score_details
            })

        responses_2 = await asyncio.gather(*[task[1] for task in tasks_2])
        responses_2_clean = []
        for task, response_2 in zip(tasks_2, responses_2):
            try:
                # Remove code block markers and clean the JSON
                content = response_2.choices[0].message.content.strip()
                content = re.sub(r'^```json\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
                # Now extract just the JSON object
                content = re.sub(r'^.*?{', '{', content)
                content = re.sub(r'}.*$', '}', content)
                score_details = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON for {task[0]}: {str(e)}\nResponse content: {response_2.choices[0].message.content}")
                score_details = {}
                continue
            responses_2_clean.append({
                "score_past": score_details
            })

        output = []
        if len(responses_1_clean) != len(responses_2_clean):
            raise ValueError("Responses 1 and 2 must have the same length")
        for response_1, response_2 in zip(responses_1_clean, responses_2_clean):

            try:
                score_details = {
                    "score_current": response_1['score_current']['score_details'],
                    "score_past": response_2['score_past']['score_details']
                }
                output.append({
                    "profile_id": response_1['profile_id'], 
                    "score": (int(score_details['score_current']['score']) + int(score_details['score_past']['score']))/2,
                    "score_details": score_details,
                    "profile_details": response_1['profile_details']
                })

            except json.JSONDecodeError as e:
                print(f"Skipping {task[0]} because the response is not a valid JSON")
                continue
            
        return output

    # Run the async function
    output = asyncio.run(process_profiles())

    with open(os.path.join(os.path.dirname(__file__), 'final_results_test.json'), 'w') as f:
        json.dump(output, f, indent=4)
