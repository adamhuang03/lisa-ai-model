from re import search
from typing import List, Tuple, Optional

from httpx import Limits
from custom_lib.linkedin_wrapper import LinkedinWrapper
import math
import logging
import traceback
import json
import pandas as pd
import os
from openai import OpenAI
from dataclasses import dataclass, asdict
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from prompt.extraction import OPENAI_EXTRACTION_PROMPT, POST_PROMPT_INSTR

def parse_input_prompt(prompt: str, openai_client: OpenAI) -> dict:
    """
    Parse the input prompt using OpenAI to extract search parameters
    Example prompt: "Find 10 Canadian investment banking analysts in NY for Moelis"
    """
    try:
        # Create the complete prompt for OpenAI
        full_prompt = f"{OPENAI_EXTRACTION_PROMPT}\n\nInput text: {prompt}\n\n{POST_PROMPT_INSTR}"
        
        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # or "gpt-3.5-turbo" for faster, cheaper results
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured information from a given text, and checks to ensure that the following requirements listed are met. "},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.1  # Low temperature for more consistent results
        )
        
        # Extract the JSON response
        json_str = response.choices[0].message.content.strip()
        # Clean up the response if it contains markdown formatting
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].strip()
            
        parsed_data = json.loads(json_str)
        logger.info("Successfully parsed prompt with OpenAI")
        return parsed_data
        
    except Exception as e:
        logger.error(f"Error parsing prompt with OpenAI: {str(e)}")
        logger.info("Falling back to default parsing")
        return {
            "target_total": 10,
            "keyword_industry": "investment banking",
            "companies": [
                {
                    "name": "Moelis",
                    "locations": [
                        {
                            "location": "New York",
                            "target_per_location": 10
                        }
                    ]
                }
            ],
            "additional_filters": {
                "positions": ["analyst", "associate", "vp"],
                "include_cad_schools_on_fill_search": True
            }
        }

def prepare_search_parameters(
    # count: int,
    # current_company: List[str] = None,
    # locations: List[str] = None,
    prompt: str = None,
    openai_client: Optional[OpenAI] = None
) -> Tuple[any, any]:
    """
    Prepare search parameters and calculate target distribution for companies and locations.
    
    Args:
        count: Total number of results to retrieve
        current_company: List of company URNs
        locations: List of location URNs
        prompt: Optional prompt string to use OpenAI for parameter extraction
        openai_client: Optional OpenAI client for prompt parsing
    
    Returns:
        List of tuples containing (company_urn, [(location_urn, target_count)])
    """
    if prompt and openai_client:
        # Use prompt-based parameter extraction
        logger.info("Starting prompt-based parameter extraction")
        parsed_data = parse_input_prompt(prompt, openai_client)
        logger.debug("Parsed data from prompt: %s", parsed_data)
        company_location_targets = []
        
        total_target = parsed_data["target_total"]
        companies = parsed_data["companies"]
        logger.info("Target total: %d, Number of companies: %d", total_target, len(companies))
        
        # If no companies specified in prompt, use "any"
        if not companies:
            logger.info("No specific companies found in prompt, using 'any'")
            company_location_targets = [("any", [("any", total_target)])]
        else:
            for company in companies:
                company_locations = []
                logger.debug("Processing company: %s", company["name"])
                # If no locations specified for company, use "any"
                if not company["locations"]:
                    target = company["target_per_company"] if "target_per_company" in company else total_target // len(companies)
                    logger.info("No locations specified for %s, using 'any' with target: %d", company["name"], target)
                    company_locations = [("any", target)]
                else:
                    for loc in company["locations"]:
                        company_locations.append((loc["location"], loc["target_per_location"]))
                        logger.debug("Added location for %s: %s with target: %d", 
                                   company["name"], loc["location"], loc["target_per_location"])
                company_location_targets.append((company["name"], company_locations))
        
        logger.info("Prepared search targets from prompt: %s", company_location_targets)
        return (parsed_data, company_location_targets)
    
    # # Fall back to original logic if no prompt or OpenAI client provided
    # logger.info("Preparing search parameters with count=%d, companies=%s, locations=%s",
    #            count, current_company, locations)
    
    # locations = locations or []
    # current_company = current_company or []
    # company_location_targets = []
    
    # if not current_company:
    #     # If no companies specified, proceed with location-only logic
    #     location_targets = []
    #     if not locations:
    #         location_targets = [("any", count)]
    #         logger.info("No locations provided, setting single target: ('any', %d)", count)
    #     else:
    #         base_per_location = count // len(locations)
    #         remainder = count % len(locations)
            
    #         for i, loc in enumerate(locations):
    #             target = base_per_location + (1 if i < remainder else 0)
    #             location_targets.append((loc, target))
    #     company_location_targets = [("any", location_targets)]
    #     logger.info("No companies provided, using location-only targets: %s", location_targets)
    # else:
    #     # Handle company-based distribution
    #     if len(current_company) * (len(locations) if locations else 1) > count:
    #         # If total combinations exceed count, distribute by company first
    #         base_per_company = count // len(current_company)
    #         company_remainder = count % len(current_company)
            
    #         # Take only as many companies as needed based on count
    #         for i, company in enumerate(current_company[:count]):
    #             company_target = base_per_company + (1 if i < company_remainder else 0)
                
    #             # Now distribute within each company by location
    #             company_location_list = []
    #             if not locations:
    #                 company_location_list = [("any", company_target)]
    #             else:
    #                 base_per_location = company_target // len(locations)
    #                 location_remainder = company_target % len(locations)
                    
    #                 for j, loc in enumerate(locations):
    #                     location_target = base_per_location + (1 if j < location_remainder else 0)
    #                     if location_target > 0:
    #                         company_location_list.append((loc, location_target))
                
    #             company_location_targets.append((company, company_location_list))
    #     else:
    #         # If combinations don't exceed count, use all companies
    #         base_per_company = count // len(current_company)
    #         company_remainder = count % len(current_company)
            
    #         for i, company in enumerate(current_company):
    #             company_target = base_per_company + (1 if i < company_remainder else 0)
                
    #             # Distribute within company by location
    #             company_location_list = []
    #             if not locations:
    #                 company_location_list = [("any", company_target)]
    #             else:
    #                 base_per_location = company_target // len(locations)
    #                 location_remainder = company_target % len(locations)
                    
    #                 for j, loc in enumerate(locations):
    #                     location_target = base_per_location + (1 if j < location_remainder else 0)
    #                     if location_target > 0:
    #                         company_location_list.append((loc, location_target))
                
    #             company_location_targets.append((company, company_location_list))
    
    # logger.info("Prepared search targets: %s", company_location_targets)
    # return company_location_targets

def get_location_ids(
    linkedin: LinkedinWrapper,
    locations: List[Tuple[str, int]]
) -> List[Tuple[str, int]]:
    """
    Get location URNs from location names and replace them with their IDs.
    
    Args:
        linkedin: LinkedinWrapper instance
        locations: List of (location_name, target_count)
    
    Returns:
        List of (location_id, target_count) with location names replaced by IDs
    """
    logger.info("Starting location ID resolution for %d locations", len(locations))
    logger.info("Input locations: %s", locations)
    adjusted_locations = []
    
    for location_name, target_count in locations:
        logger.info("Processing location: %s with target count: %d", location_name, target_count)
        if location_name == "any":
            logger.info("Location is 'any', skipping search")
            adjusted_locations.append(("any", target_count))
            continue
            
        # Search for location using LinkedIn API
        logger.info("Searching LinkedIn for location: %s", location_name)
        try:
            location_id = linkedin.search_geo(keywords=location_name)
            if location_id:
                logger.info("Found location ID for %s: %s", location_name, location_id)
                adjusted_locations.append((location_id, target_count))
                logger.info("Added location to adjusted targets: (%s, %d)", location_id, target_count)
            else:
                logger.warning("No results found for location: %s", location_name)
        except Exception as e:
            logger.error("Error searching for location %s: %s", location_name, str(e))
            continue
    
    logger.info("Completed location ID resolution. Final adjusted locations: %s", adjusted_locations)
    return adjusted_locations

def get_company_ids(
    linkedin: LinkedinWrapper,
    search_targets: List[Tuple[str, List[Tuple[str, int]]]],
) -> List[Tuple[str, List[Tuple[str, int]]]]:
    """
    Get company URNs from search targets and replace company names with their IDs.
    Also resolves location IDs for each company.
    
    Args:
        linkedin: LinkedinWrapper instance
        search_targets: List of (company_name, [(location, target_count)])
    
    Returns:
        List of (company_id, [(location_id, target_count)]) with names replaced by IDs
    """
    logger.info("Starting company ID resolution for %d targets", len(search_targets))
    logger.info("Input search targets: %s", search_targets)
    adjusted_search_targets = []
    
    for company_name, locations in search_targets:
        logger.info("Processing company: %s with locations: %s", company_name, locations)
        if company_name == "any":
            logger.info("Company is 'any', skipping search")
            # Even for 'any' company, we need to resolve location IDs
            adjusted_locations = get_location_ids(linkedin, locations)
            adjusted_search_targets.append(("any", adjusted_locations))
            continue
            
        # Search for company using LinkedIn API
        logger.info("Searching LinkedIn for company: %s", company_name)
        search_results = linkedin.search_companies(
            keywords=[company_name],
            limit=10,
            offset=0
        )
        logger.info("Search returned %d results", len(search_results) if search_results else 0)
        if not search_results:
            logger.warning("No results found for company: %s", company_name)
            continue
            
        # Use the first result's URN ID
        company_id = search_results[0]["urn_id"]
        company_found_name = search_results[0]["name"]
        logger.info("Found company ID for %s (matched with: %s): %s", 
                   company_name, company_found_name, company_id)
        
        # Resolve location IDs for this company
        adjusted_locations = get_location_ids(linkedin, locations)
        adjusted_search_targets.append((company_id, adjusted_locations))
        logger.info("Added company to adjusted targets: (%s, %s)", company_id, adjusted_locations)
    
    logger.info("Adjusted search targets with company and location IDs: %s", adjusted_search_targets)
    return adjusted_search_targets

def execute_search(
    linkedin: LinkedinWrapper,
    search_targets: List[Tuple[str, List[Tuple[str, int]]]],
    search_keyword: str = "",
    school_urn_id: str = "",
    existing_urn_ids: List[str] = None,
    offset: int = 0,
    cad_school_check: bool = False
) -> List[Tuple[str, List[Tuple[str, int, int, List[dict]]]]]:
    """
    Execute LinkedIn search based on prepared parameters.
    
    Args:
        linkedin: LinkedinWrapper instance
        search_targets: List of (company_urn, [(location_urn, target_count)])
        search_keyword: Role/keyword to search for
        school_urn_id: School URN ID
        existing_urn_ids: List of URN IDs to exclude
        offset: Search offset
        cad_school_check: Whether to check against CAD school list
    
    Returns:
        List of (company_urn, [(location_urn, target_count, actual_count, people_list)])
    """
    logger.info("Starting search execution with targets: %s", search_targets)
    existing_urn_ids = existing_urn_ids or []
    search_results = []
    total_target = sum(sum(target for _, target in company_targets) 
                      for _, company_targets in search_targets)
    total_remaining = total_target
    
    for company_idx, (company_urn, original_location_targets) in enumerate(search_targets):
        if total_remaining <= 0:
            logger.info("Total target met. Skipping remaining companies.")
            break
        
        company_results = []
        company_total_found = 0
        remaining_locations = original_location_targets.copy()
        company_target = min(total_remaining, sum(target for _, target in original_location_targets))
        
        logger.info("Processing company '%s' with target %d", company_urn, company_target)
        
        while remaining_locations and company_target > company_total_found:
            # current_target = company_target - company_total_found
            # num_remaining_locs = len(remaining_locations)
            
            # base_per_location = current_target // num_remaining_locs
            # extra = current_target % num_remaining_locs
            
            loc_urn, original_target = remaining_locations[0]
            # adjusted_target = min(total_target, base_per_location + (1 if extra > 0 else 0))
            adjusted_target = original_target
            
            if adjusted_target > 0:
                search_params = {
                    "keywords": search_keyword,
                    "schools": [school_urn_id] if school_urn_id else None,
                    "limit": 10,
                    "offset": offset
                }
                
                if loc_urn != "any":
                    search_params["regions"] = [loc_urn]
                if company_urn != "any":
                    search_params["current_company"] = [company_urn]
                
                try:
                    logger.info("Executing LinkedIn search with params: %s", search_params)
                    results = linkedin.search_people(**search_params)
                    
                    people_found = []
                    for person in results:
                        if len(people_found) >= adjusted_target:
                            break
                        if person.get("urn_id") not in existing_urn_ids:
                            people_found.append((person, school_urn_id))
                    
                    found_count = len(people_found)
                    company_total_found += found_count
                    
                    logger.info("Found %d/%d people for location '%s'", 
                              found_count, adjusted_target, loc_urn)
                    
                    company_results.append((loc_urn, adjusted_target, found_count, people_found))
                    
                except Exception as e:
                    logger.error("Error searching location '%s': %s", loc_urn, str(e))
                    logger.error(traceback.format_exc())
                    company_results.append((loc_urn, adjusted_target, 0, []))
            else:
                company_results.append((loc_urn, 0, 0, []))
            
            remaining_locations.pop(0)
        
        for loc_urn, _ in remaining_locations:
            company_results.append((loc_urn, 0, 0, []))
        
        search_results.append((company_urn, company_results))
        total_remaining -= company_total_found
        
        logger.info("Company '%s' found %d/%d people. Total remaining: %d", 
                  company_urn, company_total_found, company_target, total_remaining)
    
    if cad_school_check and school_urn_id:
        search_results = _handle_cad_school_search(
            linkedin, search_results, search_keyword, school_urn_id, 
            existing_urn_ids, offset
        )
    
    return search_results

def _handle_cad_school_search(
    linkedin: LinkedinWrapper,
    search_results: List[Tuple[str, List[Tuple[str, int, int, List[dict]]]]],
    search_keyword: str,
    school_urn_id: str,
    existing_urn_ids: List[str],
    offset: int
) -> List[Tuple[str, List[Tuple[str, int, int, List[dict]]]]]:
    """
    Handle CAD school search as a supplementary search when primary search doesn't meet targets.
    """
    try:
        logger.info("Starting CAD school search with keyword='%s', school_urn_id='%s'", 
                   search_keyword, school_urn_id)
        
        # Load and process CAD schools
        logger.debug("Loading CAD schools from data/cad_schools.json")
        cad_schools = json.loads(open("data/cad_schools.json", "r").read())
        cad_school_values = list(cad_schools.values())
        logger.info("Loaded %d CAD schools", len(cad_school_values))
        
        if school_urn_id in cad_school_values:
            cad_school_values.remove(school_urn_id)
            logger.info("Removed current school_urn_id from CAD schools list. Remaining: %d", 
                        len(cad_school_values))
        
        final_results = []
        logger.info("Processing %d company results from initial search", len(search_results))
        
        for company_idx, (company_urn, location_results) in enumerate(search_results):
            logger.info("Processing company %d/%d: '%s' with %d location results", 
                        company_idx + 1, len(search_results), company_urn, len(location_results))
            company_final_results = []
            
            for loc_idx, (loc_urn, target, current_count, found_people) in enumerate(location_results):
                logger.info("Location %d/%d: '%s' (target: %d, current: %d)", 
                           loc_idx + 1, len(location_results), loc_urn, target, current_count)
                
                if current_count < target:
                    remaining_target = target - current_count
                    logger.info("Need %d more results for location '%s'", remaining_target, loc_urn)
                    
                    try:
                        search_params = {
                            "keywords": search_keyword,
                            "schools": cad_school_values,
                            "limit": 10,
                            "offset": offset,
                            "or_schools": True
                        }
                        if loc_urn != "any":
                            search_params["regions"] = [loc_urn]
                        if company_urn != "any":
                            search_params["current_company"] = [company_urn]
                        
                        logger.info("Executing CAD school search with params: %s", search_params)
                        results = linkedin.search_people(**search_params)
                        logger.info("Retrieved %d results from LinkedIn API", len(results))
                        
                        initial_count = current_count
                        for person in results:
                            if current_count >= target:
                                logger.info("Reached target count (%d). Stopping search.", target)
                                break
                            if person.get("urn_id") not in existing_urn_ids:
                                found_people.append((person, "from_cad_school"))
                                current_count += 1
                        
                        new_results = current_count - initial_count
                        logger.debug("Added %d new results from CAD schools for location '%s'", 
                                   new_results, loc_urn)
                        
                    except Exception as e:
                        logger.error("Error in CAD school search for location '%s': %s", 
                                   loc_urn, str(e))
                        logger.debug(traceback.format_exc())
                else:
                    logger.debug("Skipping location '%s' - target already met (%d/%d)", 
                               loc_urn, current_count, target)
                
                company_final_results.append((loc_urn, target, current_count, found_people))
            
            logger.debug("Completed processing company '%s'. Adding to final results.", company_urn)
            final_results.append((company_urn, company_final_results))
        
        total_results = sum(len(found_people) for _, location_results in final_results 
                          for _, _, _, found_people in location_results)
        logger.info("Completed CAD school search. Total results across all companies: %d", 
                   total_results)
        return final_results
        
    except Exception as e:
        logger.error("Error in CAD school search: %s", str(e))
        logger.error(traceback.format_exc())
        logger.info("Returning original search results due to CAD school search error")
        return search_results

def search_people(
    linkedin: LinkedinWrapper,
    count: int = 10,
    search_keyword: str = "",
    school_urn_id: str = "",
    current_company: List[str] = None,
    locations: List[str] = None,
    cad_school_check: bool = False,
    existing_urn_ids: List[str] = None,
    offset: int = 0
) -> List[Tuple[str, List[Tuple[str, int, int, List[dict]]]]]:
    """
    Search for people on LinkedIn based on various criteria
    
    Args:
        linkedin: LinkedinWrapper instance
        count: Number of people to retrieve (default: 10)
        search_keyword: Role/keyword to search for
        school_urn_id: School URN ID
        current_company: List of company URNs
        locations: List of location URNs
        cad_school_check: Whether to check against CAD school list
        existing_urn_ids: List of URN IDs to exclude
        offset: Search offset
    
    Returns:
        List of tuples containing (company_urn, [(location_urn, target_count, actual_count, people_list)])
    """
    try:
        # Step 1: Prepare search parameters and calculate targets
        search_targets = prepare_search_parameters(
            # count=count,
            # current_company=current_company,
            # locations=locations,
            prompt=None,
            openai_client=None
        )

        # Debugging: Print prepared search targets
        logger.info("Prepared search targets: %s", search_targets)
        
        # Step 2: Execute search with prepared parameters
        return execute_search(
            linkedin=linkedin,
            search_targets=search_targets,
            search_keyword=search_keyword,
            school_urn_id=school_urn_id,
            existing_urn_ids=existing_urn_ids,
            offset=offset,
            cad_school_check=cad_school_check
        )
    except Exception as e:
        logger.error("Error in search_people: %s", str(e))
        logger.error(traceback.format_exc())
        raise

def extract_linkedin_data(results: list):
    # Lists to store the data
    data = []
    accumulator = []
    
    # Iterate through companies
    for company_data in results:
        company_urn = company_data[0]
        location_list = company_data[1]
        # Iterate through locations within each company
        for location_data in location_list:
            people_list = location_data[3]  # Index 3 contains the list of people
            for person in people_list:
                person_data = person[0]  # Get person dictionary
                urn_id = person_data.get("urn_id")
                url = person_data.get("url")
                data.append({
                    "urn_id": urn_id,
                    "url": url
                })
                accumulator.append(urn_id)

    with open("z.3)output/results.json", "w") as f:
        json.dump(results, f, indent=4)
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Save to CSV
    df.to_csv("z.3)output/linkedin_data.csv", index=False)
    print(f"Saved {len(data)} records to z.3)output/linkedin_data.csv")

    # Save accumulator to JSON
    if os.path.exists("z.2)craft_input/accumulator.json"):
        with open("z.2)craft_input/accumulator.json", "r") as f:
            existing_urn_ids = json.load(f)
        existing_urn_ids.extend(accumulator)
        with open("z.2)craft_input/accumulator.json", "w") as f:
            json.dump(existing_urn_ids, f, indent=4)
    else:
        with open("z.2)craft_input/accumulator.json", "w") as f:
            json.dump(accumulator, f, indent=4)

    print(f"Saved {len(accumulator)} records to z.2)craft_input/accumulator.json")

if __name__ == "__main__":
    # this is good for 1 firm search at a time

    import json, os
    from pprint import pprint

    prompt_1 = "Find 10 Canadian investment banking analysts in NY for Moelis"
    prompt_2 = """
    Looking for people working in investment banking in the US preferably with a Canadian background from firms such as Morgan Stanley, Rothschild, Goldman Sachs, Greenhill, Bank of America, Nomura, Mizuho, Gordon Dyal, BDT & MSD, Oppenheimer, Baird, Liontree, Citi, Barclays, Moelis, Lazard, AGC Partners, BC Partners, Deutsche Bank. Separate from each office such as Los Angeles, San Francisco, New York, Chicago, Houston. Per each office maximum 2 candidates and are not already included in my list of reachouts, Prioritize the West Coast as I've been getting more response rates and prioritize banks that are known to sponsor visas.
    """
    prompt_3 = """
    Please find and draft 10-15 emails for investment banking analysts or associates that work in either San Francisco, Los Angeles, or Menlo Park. Firms that I want to reach out to people at are Moelis and Evercore. Please find people from Canadian universities, with descending priority of this list of schools: University of Waterloo, Wilfrid Laurier University (Lazaridis), University of Western Ontario (Ivey), Queens University (Smith), University of Toronto. If none at these schools, then any professionals that went to non-ivey league schools, or went to school outside of the United States. Please prioritize any that may have the following on their Linkedin: Previously worked at KPMG/the big 4, internship at Dawson Partners/Whitehorse Liquidity, high school/hometown of Mississauga.

If they went to the University of Waterloo, please use template 2. If they went to a Canadian university that's not Waterloo, use template 3. If they went to a non-Canadian school, use template 1. If they do not have their product or coverage group on their Linkedin, please remove the line from the template
    """
    prompt_4 = """
    Looking for people working in investment banking in the US preferably with a Canadian background from firms such as Morgan Stanley, Rothschild, Goldman Sachs, Greenhill, Bank of America, Nomura, Mizuho, Gordon Dyal, BDT & MSD, Oppenheimer, Baird, Liontree, Citi, Barclays, Moelis, Lazard, AGC Partners, BC Partners, Deutsche Bank. Separate from each office such as Los Angeles, San Francisco, New York, Chicago, Houston. Per each office maximum 2 candidates and are not already included in my list of reachouts, Prioritize the West Coast as I've been getting more response rates and prioritize banks that are known to sponsor visas.
    """

    prompt_prod = """
    
    40 Investment Banking, Corporate Banking and Global Markets Associates from CIBC who have graduated from any Canadian University and have 2+ years of experience in the role!

    """
    # HERE EDIT PROMPT
    
    prompt = prompt_prod

    # ==================================================================

    from dotenv import load_dotenv
    load_dotenv()
    openai = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )
    linkedin_user = os.getenv("LINKEDIN_USER")
    linkedin_password = os.getenv("LINKEDIN_PASSWORD")
    linkedin = LinkedinWrapper(linkedin_user, linkedin_password, debug=True)
    # ==================================================================

    search_targets = prepare_search_parameters(
        prompt=prompt,
        openai_client=openai
    )

    params = search_targets[0].copy()
    params['include_cad_schools'] = params['additional_filters']['include_cad_schools_on_fill_search']
    params['positions'] = params['additional_filters']['positions']
    params.pop("companies")
    params.pop("additional_filters")
    params_clean = params 
    search_targets_clean = search_targets[1]

    # Debugging: Print prepared search targets
    logger.info("Prepared search targets: %s", search_targets[1])
    with open("z.1)search_input/search_targets.json", "w") as f:
        json.dump(search_targets_clean, f, indent=4)
    with open("z.1)search_input/search_targets_adjusted.json", "w") as f:
        json.dump(search_targets_clean, f, indent=4)
    with open("z.1)search_input/params.json", "w") as f:
        json.dump(params_clean, f, indent=4)

    # ==================================================================

    pause = input("Update search_targets.json in z.1)search_input/adjusted. Press enter to continue...")
    
    with open("z.1)search_input/search_targets_adjusted.json", "r") as f:
        search = json.load(f)

    updated_search = get_company_ids(linkedin, search)
    with open("z.1)search_input/search_targets_final.json", "w") as f:
        json.dump(updated_search, f, indent=4)

    # ==================================================================

    pause = input("Ensure params.json and search_targets.json are correct. Press enter to continue...")

    with open("z.1)search_input/search_targets_final.json", "r") as f:
        search = json.load(f)
    with open("z.1)search_input/params.json", "r") as f:
        params = json.load(f)

    existing_urn_ids = []
    if os.path.exists("z.2)input/accumulator.json"):
        with open("z.2)input/accumulator.json", "r") as f:
            existing_urn_ids = json.load(f)

    school_urn_id = "85465247"

    # # Step 2: Execute search with prepared parameters
    results = execute_search(
        linkedin=linkedin,
        search_targets=search,
        search_keyword=params['keyword_industry'],
        school_urn_id=school_urn_id,
        existing_urn_ids=existing_urn_ids,
        offset=0,
        cad_school_check=params['include_cad_schools']
    )

    # if os.path.exists("input/accumulator.json"):
    #     with open("input/accumulator.json", "r") as f:
    #         params["existing_urn_ids"] = json.load(f)

    # # pprint(params)

    # linkedin = LinkedinWrapper("productionadamh@gmail.com", "gptproject135764", debug=True)
    # results = search_people(linkedin, **params)
    # with open("output/results.json", "w") as f:
    #     json.dump(results, f, indent=4)

    extract_linkedin_data(results)
