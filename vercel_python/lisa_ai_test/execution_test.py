from custom_lib.automail_ai_search_v2 import *
from custom_lib.automail_ai_craft import *
from custom_lib.linkedin_wrapper import *
import json
import os
from openai import OpenAI

def main():
    # Initialize OpenAI client
    client = OpenAI()
    
    # Load LinkedIn credentials from environment variables
    username = os.getenv("LINKEDIN_USERNAME")
    password = os.getenv("LINKEDIN_PASSWORD")
    
    # Initialize LinkedIn wrapper
    linkedin = LinkedinWrapper(username, password)
    
    # Example search parameters
    search_keyword = "investment banking analyst"
    locations = ["New York", "San Francisco", "Chicago"]
    companies = ["Goldman Sachs", "Morgan Stanley", "JP Morgan"]
    count = 10
    
    try:
        # Execute search
        results = search_people(
            linkedin=linkedin,
            count=count,
            search_keyword=search_keyword,
            current_company=companies,
            locations=locations
        )
        
        # Extract and process results
        processed_data = extract_linkedin_data(results)
        
        # Save results
        with open("search_results.json", "w") as f:
            json.dump(processed_data, f, indent=2)
            
        # Enrich profiles
        enriched_profiles = multi_enrich_persons(linkedin, [p["public_id"] for p in processed_data])
        
        # Save enriched profiles
        with open("enriched_profiles.json", "w") as f:
            json.dump(enriched_profiles, f, indent=2)
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    main()
