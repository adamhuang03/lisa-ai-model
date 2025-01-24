from re import search
from typing import Any, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import os
from openai import AsyncOpenAI, OpenAI
import csv
from io import StringIO
import logging
import json
import time
import asyncio
from fastapi.responses import JSONResponse
import traceback
import requests 
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

import sys
from pathlib import Path
# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

dummy_username = 'dummy'
dummy_password = 'dummy'

# Configure logging
# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.hasHandlers():  # Avoid adding handlers multiple times
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Import from the custom_lib directory relative to vercel_python
from custom_lib.automail_ai_craft import enrich_person, enrich_person_more, multi_enrich_persons
from custom_lib.automail_ai_search_v2 import parse_input_prompt, convert_parms_to_targets, get_company_locations_id, execute_single_search
from custom_lib.rocketreach_test import search_and_generate_emails
from prompt.email import EMAIL_SYSTEM_PROMPT
from custom_lib.linkedin_wrapper import LinkedinWrapper
from requests.cookies import RequestsCookieJar
from linkedin_api.cookie_repository import CookieRepository
from custom_lib.cookies_extractor_async import cookie_extractor_from_json

# uvicorn vercel_python.api.index:app --reload --log-level info

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Initialize LinkedIn client at startup
#     try:
#         cookie_dir = 'custom_lib/'
#         cookie_repo = CookieRepository(cookies_dir=cookie_dir)
#         cookies = cookie_repo.get(os.getenv("LINKEDIN_USER"))
#         if cookies and isinstance(cookies, RequestsCookieJar):
#             logger.info("Successfully loaded cookies from repository")
#             logger.info(f"Cookie names: {[cookie.name for cookie in cookies]}")
#         else:
#             logger.warning("No valid cookies found in repository")
#             cookies = None

#         logger.info("Initializing LinkedIn client")
#         linkedin_client = LinkedinWrapper(
#             username=os.getenv("LINKEDIN_USER"),
#             password=os.getenv("LINKEDIN_PASSWORD"),
#             cookies=cookies,
#             authenticate=True,
#             refresh_cookies=False,
#             debug=True
#         )
        
#         # Store in app state
#         app.state.linkedin_client = linkedin_client
#         logger.info("LinkedIn client initialized and stored in app state")
#     except Exception as e:
#         logger.error(f"Failed to initialize LinkedIn client: {str(e)}")
#         logger.error(f"Traceback: {traceback.format_exc()}")
#         # Don't raise the exception - let the app start anyway
#         # We'll handle the missing client in the routes
    
#     yield  # Server is running
    
#     # Cleanup (if needed) when the server shuts down
#     if hasattr(app.state, 'linkedin_client'):
#         pass  # No need to close the client

# Vercel version

def init_linkedin_client():
    try:
        cookie_dir = 'custom_lib/'
        cookie_repo = CookieRepository(cookies_dir=cookie_dir)
        cookies = cookie_repo.get(os.getenv("LINKEDIN_USER"))
        if cookies and isinstance(cookies, RequestsCookieJar):
            logger.info("Successfully loaded cookies from repository")
            logger.info(f"Cookie names: {[cookie.name for cookie in cookies]}")
        else:
            logger.warning("No valid cookies found in repository")
            cookies = None

        logger.info("Initializing LinkedIn client")
        linkedin_client = LinkedinWrapper(
            username=os.getenv("LINKEDIN_USER"),
            password=os.getenv("LINKEDIN_PASSWORD"),
            cookies=cookies,
            authenticate=True,
            refresh_cookies=False,
            debug=True
        )
        return linkedin_client
    except Exception as e:
        logger.error(f"Failed to initialize LinkedIn client: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

# app = FastAPI(lifespan=lifespan)
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from typing import Dict, Any

# Define request model
class ProcessDataRequest(BaseModel):
    csv_data: str
    keyword_industry: str
    user_linkedin_url: str
    email_template: str

class PromptExtractionRequest(BaseModel):
    input: str

class CompanyLocationsRequest(BaseModel):
    input: list
    cookies: List[Dict[str, Any]]

class GetCompanyRequest(BaseModel):
    company_public_id: str
    cookies: List[Dict[str, Any]]

class StandardInputRequest(BaseModel):
    input: str
    cookies: List[Dict[str, Any]]

class SendConnectionRequest(BaseModel):
    public_id: str
    message: str
    cookies: List[Dict[str, Any]]

class ExecutionSearch(BaseModel):
    company_urn: str
    company_name_for_passthrough: str
    location_urn: str
    search_keyword: str = ""
    school_urn_id: str = ""
    existing_public_ids: list = None
    offset: int = 0
    target_count: int = 10
    use_cad: bool = False
    cookies: List[Dict[str, Any]]

class SearchPeopleRequest(BaseModel):
    keywords: str
    past_companies: list
    or_past_companies: bool
    limit: int
    offset: int
    cookies: List[Dict[str, Any]]

class EmailAddressRequest(BaseModel):
    names: list
    company: str

class DraftEmailsRequest(BaseModel):
    url_list: list
    keyword_industry: str
    user_linkedin_url: str
    email_template: str
    cookies: List[Dict[str, Any]]

class EnrichProfileRequest(BaseModel):
    linkedin_url: str
    cookies: List[Dict[str, Any]]

@app.post("/extract-prompt-data")
async def extract_prompt_data(request: PromptExtractionRequest) -> dict:
    logger.info(f"Received prompt: {request.input}")
    try: 
        # Send initial checkpoint
        openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        logger.info("Created OpenAI client")
        output = parse_input_prompt(prompt=request.input, openai_client=openai_client)
        logger.info(f"Successfully parsed prompt with OpenAI: {output}")
        company_location_targets = convert_parms_to_targets(output)
        logger.info(f"Successfully converted parameters to targets: {company_location_targets}")
        return JSONResponse(content={
            "params": output,
            "targets": company_location_targets
        }, media_type="application/json")

    except Exception as e:
        logger.error(f"Error in extract_prompt_data: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-company-locations-id")
async def get_ids(request: CompanyLocationsRequest) -> dict:
    logger.info(f"Received prompt: {request.input}")
    try:
        # if not hasattr(app.state, 'linkedin_client'):
        #     raise HTTPException(status_code=500, detail="LinkedIn client not initialized")
            
        # # # Use the client from app state
        # linkedin_client = app.state.linkedin_client

        # linkedin_client = init_linkedin_client()
        cookies = request.cookies
        cookies_jar = cookie_extractor_from_json(cookies)
        linkedin_client = LinkedinWrapper(dummy_username, dummy_password, cookies=cookies_jar, debug=True)
        if not linkedin_client:
            raise HTTPException(status_code=500, detail="Failed to initialize LinkedIn client")

        result = get_company_locations_id(
            linkedin=linkedin_client, search_target=request.input)
        logger.info(f"Successfully got company locations: {result}")

        target_list = []
        company_id, locations, company_name = result
        if locations:
            for location in locations:
                target_list.append([company_id, location[0], location[1], company_name])
        else:
            target_list.append([company_id, "", 0, company_name])

        # Your existing logic here using linkedin_client
        return JSONResponse(content={
            "result": result,
            "targets": target_list
        }, media_type="application/json")

    except Exception as e:
        logger.error(f"Error in get_company_locations_id: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute-single-search")
async def get_execution_search(request: ExecutionSearch) -> dict:
    logger.info(f"Received prompt: {request}")
    try:
        # if not hasattr(app.state, 'linkedin_client'):
        #     raise HTTPException(status_code=500, detail="LinkedIn client not initialized")
            
        # # # Use the client from app state
        # linkedin_client = app.state.linkedin_client
        cookies = request.cookies
        cookies_jar = cookie_extractor_from_json(cookies)
        linkedin_client = LinkedinWrapper(dummy_username, dummy_password, cookies=cookies_jar, debug=True)

        if not linkedin_client:
            raise HTTPException(status_code=500, detail="Failed to initialize LinkedIn client")

        result = execute_single_search(
            linkedin=linkedin_client,
            company_name_for_passthrough=request.company_name_for_passthrough,
            company_urn=request.company_urn,
            location_urn=request.location_urn,
            search_keyword=request.search_keyword,
            school_urn_id=request.school_urn_id,
            existing_public_ids=request.existing_public_ids,
            offset=request.offset,
            target_count=request.target_count,
            use_cad=request.use_cad,
        )
        logger.info(f"Successfully executed single search: {result}")   

        # Your existing logic here using linkedin_client
        return JSONResponse(content={
            "result": result
        }, media_type="application/json")

    except Exception as e:
        logger.error(f"Error in get_company_locations_id: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search-people")
async def get_search_people(request: SearchPeopleRequest) -> dict:
    logger.info(f"Received prompt: {request}")
    try:
        cookies = request.cookies
        cookies_jar = cookie_extractor_from_json(cookies)
        linkedin_client = LinkedinWrapper(dummy_username, dummy_password, cookies=cookies_jar, debug=True)
        if not linkedin_client:
            raise HTTPException(status_code=500, detail="Failed to initialize LinkedIn client")

        result = linkedin_client.search_people(
            keywords=request.keywords,
            past_companies=request.past_companies,
            or_past_companies=request.or_past_companies,
            limit=request.limit,
            offset=request.offset
        )
        logger.info(f"Successfully executed single search: {result}")   

        # Your existing logic here using linkedin_client
        return JSONResponse(content={
            "result": result
        }, media_type="application/json")

    except Exception as e:
        logger.error(f"Error in get_company_locations_id: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/format-email-addresses")
async def get_email_addresses(request: EmailAddressRequest) -> dict:
    logger.info(f"Received prompt: {request}")
    try:
        openai_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        logger.info("Created OpenAI client")

        emails = await search_and_generate_emails(
            async_openai_client=openai_client,
            company=request.company,
            names=request.names
        )
        logger.info(f"Successfully generated email addresses: {emails}")

        if not emails:
            return JSONResponse(content={
                "format": "",
                "result": []
            }, media_type="application/json")
        else:
            # Your existing logic here using linkedin_client
            return JSONResponse(content={
                "format": emails[0],
                "result": emails[1]
            }, media_type="application/json")

    except Exception as e:
        logger.error(f"Error in get_company_locations_id: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-school-id") # TBD
async def get_school_id(request: EnrichProfileRequest) -> dict:
    logger.info(f"Received prompt: {request}")
    try:
        # if not hasattr(app.state, 'linkedin_client'):
        #     raise HTTPException(status_code=500, detail="LinkedIn client not initialized")
            
        # # # Use the client from app state
        # linkedin_client = app.state.linkedin_client

        cookies = request.cookies
        cookies_jar = cookie_extractor_from_json(cookies)
        linkedin_client = LinkedinWrapper(dummy_username, dummy_password, cookies=cookies_jar, debug=True)
        if not linkedin_client:
            raise HTTPException(status_code=500, detail="Failed to initialize LinkedIn client")

        result = enrich_person(
            linkedin=linkedin_client,
            value=request.linkedin_url,
            url_value=True
        )
        logger.info(f"Successfully enriched person: {result}")
        education_set = result.get("education", [])

        # Your existing logic here using linkedin_client
        return JSONResponse(content={
            "result": education_set
        }, media_type="application/json")

    except Exception as e:
        logger.error(f"Error in get_company_locations_id: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/enrich-profile") # TBD
async def enrich_profile(request: EnrichProfileRequest) -> dict:
    logger.info(f"Received prompt: {request}")
    try:

        cookies = request.cookies
        cookies_jar = cookie_extractor_from_json(cookies)
        linkedin_client = LinkedinWrapper(dummy_username, dummy_password, cookies=cookies_jar, debug=True)
        if not linkedin_client:
            raise HTTPException(status_code=500, detail="Failed to initialize LinkedIn client")

        result = enrich_person(
            linkedin=linkedin_client,
            value=request.linkedin_url,
            url_value=True
        )

        # Your existing logic here using linkedin_client
        return JSONResponse(content={
            "result": result
        }, media_type="application/json")

    except Exception as e:
        logger.error(f"Error in get_company_locations_id: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/enrich-profile-more") # TBD
async def enrich_profile_more(request: EnrichProfileRequest) -> dict:
    logger.info(f"Received prompt: {request}")
    try:

        cookies = request.cookies
        cookies_jar = cookie_extractor_from_json(cookies)
        linkedin_client = LinkedinWrapper(dummy_username, dummy_password, cookies=cookies_jar, debug=True)
        if not linkedin_client:
            raise HTTPException(status_code=500, detail="Failed to initialize LinkedIn client")

        result = enrich_person_more(
            linkedin=linkedin_client,
            value=request.linkedin_url,
            url_value=True
        )

        # Your existing logic here using linkedin_client
        return JSONResponse(content={
            "result": result
        }, media_type="application/json")

    except Exception as e:
        logger.error(f"Error in get_company_locations_id: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-company") # TBD
async def get_company(request: GetCompanyRequest) -> dict:
    logger.info(f"Received prompt: {request}")
    try:

        cookies = request.cookies
        cookies_jar = cookie_extractor_from_json(cookies)
        linkedin_client = LinkedinWrapper(dummy_username, dummy_password, cookies=cookies_jar, debug=True)
        if not linkedin_client:
            raise HTTPException(status_code=500, detail="Failed to initialize LinkedIn client")

        result = linkedin_client.get_company(public_id=request.company_public_id)

        # Your existing logic here using linkedin_client
        return JSONResponse(content={
            "result": result
        }, media_type="application/json")

    except Exception as e:
        logger.error(f"Error in get_company_locations_id: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-company-id") # TBD
async def get_company_id(request: StandardInputRequest) -> dict:
    logger.info(f"Received prompt: {request}")
    try:
        cookies = request.cookies
        cookies_jar = cookie_extractor_from_json(cookies)
        linkedin_client = LinkedinWrapper(dummy_username, dummy_password, cookies=cookies_jar, debug=True)
        if not linkedin_client:
            raise HTTPException(status_code=500, detail="Failed to initialize LinkedIn client")

        search_results = linkedin_client.search_companies(
            keywords=[request.input],
            limit=10,
            offset=0
        )        
        # Use the first result's URN ID
        company_id = search_results[0]["urn_id"]
        company_found_name = search_results[0]["name"]

        logger.info(f"Successfully found company: {company_id} for company name: {company_found_name}")

        # Your existing logic here using linkedin_client
        return JSONResponse(content={
            "result": [company_id, company_found_name]
        }, media_type="application/json")

    except Exception as e:
        logger.error(f"Error in get_company_locations_id: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-connection-request")
async def send_connection_request(request: SendConnectionRequest) -> dict:
    try:
        # Debug raw request
        # raw_body = await raw_request.json()
        # logger.info("=== Raw Request Data ===")
        # logger.info(f"Headers: {raw_request.headers}")
        # logger.info(f"Raw body: {raw_body}")
        
        # Debug parsed request
        logger.info("=== Parsed Request Data ===")
        logger.info(f"Request type: {type(request)}")
        logger.info(f"public_id: {request.public_id}")
        logger.info(f"message: {request.message}")
        logger.info(f"cookies: {request.cookies}")
        logger.info("=== End Request Data ===")
        

        public_id = request.public_id
        message = request.message
        cookies = request.cookies  
        # print(public_id, message, cookies)
        # result = True 

        cookies_jar = cookie_extractor_from_json(cookies)
        linkedin = LinkedinWrapper(dummy_username, dummy_password, cookies=cookies_jar, debug=True)
        try:
            result = linkedin.add_connection(
                profile_public_id=public_id,
                message=message,
            )

            if result:
                return JSONResponse(content={
                    "result": 'Request has already been sent'
                }, media_type="application/json")
            else:
                return JSONResponse(content={
                    "result": 'Request sent successfully'
                }, media_type="application/json")
        except Exception as e:
            logger.error(f"Error in send_connection_request: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return JSONResponse(content={
                "error": str(e),
                "result": 'Cookies are invalid'
            }, media_type="application/json")



    except Exception as e:
        logger.error(f"Error in get_company_locations_id: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login-linkedin") # TBD
async def login_linkedin(request: SendConnectionRequest) -> dict:
    logger.info(f"Received prompt: {request}")
    try:
        email = request.email
        password = request.password
        # public_id = request.public_id
        # message = request.message

        res = requests.get(
            f'http://trylisa.vercel.app/chat/api/playwright' +
            f'?email={email}&password={password}',
        )

        json_data = res.json()

        print(json_data)

        if 'error' in json_data:
            print(False)
            return JSONResponse(content={
                "error": 'error'
            }, media_type="application/json")
        else:
            print(True)
            return JSONResponse(content={
                "result": 'Successfully logged in',
                'cookies': json_data['cookies']
            }, media_type="application/json")

    except Exception as e:
        logger.error(f"Error in get_company_locations_id: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/draft-emails")
async def draft_emails(request: DraftEmailsRequest):
    async def generate_response():
        start_time = time.time()
        try:
            # Send initial checkpoint
            yield json.dumps({"status": "started", "message": f"Request received (t=0s)"}) + "\n"
            yield json.dumps({"status": "started", "message": f"Url List:\n{request.url_list}\n"}) + "\n"
            yield json.dumps({"status": "started", "message": f"Industry: {request.keyword_industry}\n"}) + "\n"
            yield json.dumps({"status": "started", "message": f"LinkedIn URL: {request.user_linkedin_url}\n"}) + "\n"
            yield json.dumps({"status": "started", "message": f"Email Template: {request.email_template}\n"}) + "\n"
            
            logger.info(f"Starting process_data with industry: {request}")
            
            from dotenv import load_dotenv
            load_dotenv()

            # Initialize OpenAI client
            yield json.dumps({"status": "progress", "message": f"Initializing OpenAI client (t={int(time.time() - start_time)}s)"}) + "\n"
            logger.info("Initializing OpenAI client")
            openai_client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY")
            )

            # if not hasattr(app.state, 'linkedin_client'):
            #     raise HTTPException(status_code=500, detail="LinkedIn client not initialized")
            
            # # Use the client from app state
            # linkedin_client = app.state.linkedin_client

            cookies = request.cookies
            cookies_jar = cookie_extractor_from_json(cookies)
            linkedin_client = LinkedinWrapper(dummy_username, dummy_password, cookies=cookies_jar, debug=True)
            if not linkedin_client:
                raise HTTPException(status_code=500, detail="Failed to initialize LinkedIn client")
            
            yield json.dumps({"status": "progress", "message": f"Starting profile enrichment (t={int(time.time() - start_time)}s)"}) + "\n"
            logger.info(f"Enriching user profile: {request.user_linkedin_url}")
            user_profile = enrich_person(
                linkedin=linkedin_client,
                value=request.user_linkedin_url,
                url_value=True
            )
            
            # Get the URNs (first column)
            list_of_urls = request.url_list
            
            yield json.dumps({"status": "progress", "message": f"Found {len(list_of_urls)} URLs to process, splitting between 1 client(s) (t={int(time.time() - start_time)}s)"}) + "\n"
            logger.info(f"Found {len(list_of_urls)} URLs to process, splitting {len(list_of_urls)} between clients")
            
            # Create async tasks for both clients
            logger.info("Starting parallel profile enrichment with both clients")
            
            async def process_client(client, urls, client_name, start_time):
                results = multi_enrich_persons(
                    linkedin=client,
                    values=urls,
                    url_value=True
                )
                yield json.dumps({"status": "progress", "message": f"{client_name} enriched {len(results)} profiles (t={int(time.time() - start_time)}s)"}) + "\n"
                yield results  # Yield the results as the last item
            
            # Process URLs with first client
            logger.info("Starting profile enrichment with client")
            multi_result_enriched = None
            async for item in process_client(linkedin_client, list_of_urls, "Client 1", start_time):
                if isinstance(item, str):  # If it's a progress message
                    yield item
                else:  # If it's the results
                    multi_result_enriched = item
                    # Remove education from results
                    for person in multi_result_enriched:
                        person.pop('education', None)
                
            yield json.dumps({"status": "progress", "message": f"Successfully enriched {len(multi_result_enriched)} profiles (t={int(time.time() - start_time)}s)"}) + "\n"
            
            # Send checkpoint before email drafting
            yield json.dumps({"status": "drafting", "message": f"Starting email drafting (t={int(time.time() - start_time)}s)"}) + "\n"
            
            # Process emails using batch processing
            logger.info("Starting batch email drafting")
            
            all_emails = []
            total_profiles = len(multi_result_enriched)
            batch_size = 10
            
            for i in range(0, total_profiles, batch_size):
                batch = multi_result_enriched[i:i + batch_size]
                current_batch_size = len(batch)
                logger.info(f"Processing batch {i//batch_size + 1} with {current_batch_size} profiles")
                yield json.dumps({
                    "status": "progress", 
                    "message": f"Processing email batch {i//batch_size + 1}/{(total_profiles + batch_size - 1)//batch_size} (t={int(time.time() - start_time)}s)"
                }) + "\n"
                
                # Create tasks for the batch
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
                        Role: {request.keyword_industry}
                        Email template:
                        {request.email_template}
                        """}
                    ]
                    
                    tasks.append(
                        openai_client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=messages,
                            temperature=0.3,
                            max_tokens=500
                        )
                    )
                
                # Process batch concurrently
                batch_responses = await asyncio.gather(*tasks)
                batch_emails = [response.choices[0].message.content for response in batch_responses]
                all_emails.extend(batch_emails)
                
                logger.info(f"Completed batch {i//batch_size + 1}, total emails: {len(all_emails)}/{total_profiles}")
                yield json.dumps({
                    "status": "progress",
                    "message": f"Completed {len(all_emails)}/{total_profiles} emails (t={int(time.time() - start_time)}s)"
                }) + "\n"
            
            yield json.dumps({"status": "drafting", "message": f"Preparing final CSV (t={int(time.time() - start_time)}s)"}) + "\n"
            
            # Send final CSV data
            yield json.dumps({
                "status": "completed",
                "message": f"Process completed (t={int(time.time() - start_time)}s)",
                "emails": all_emails
            }) + "\n"
            
        except Exception as e:
            logger.error(f"Error in process_data: {str(e)}", exc_info=True)
            yield json.dumps({
                "status": "error",
                "message": f"Error (t={int(time.time() - start_time)}s): {str(e)}"
            }) + "\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream"
    )

@app.get("/")
async def root():
    return {"message": "AutoMail AI API is running"}

@app.post("/process-data")
async def process_data(request: ProcessDataRequest):
    async def generate_response():
        start_time = time.time()
        try:
            # Send initial checkpoint
            yield json.dumps({"status": "started", "message": f"Request received (t=0s)"}) + "\n"
            yield json.dumps({"status": "started", "message": f"CSV Data:\n{request.csv_data}\n"}) + "\n"
            yield json.dumps({"status": "started", "message": f"Industry: {request.keyword_industry}\n"}) + "\n"
            yield json.dumps({"status": "started", "message": f"LinkedIn URL: {request.user_linkedin_url}\n"}) + "\n"
            yield json.dumps({"status": "started", "message": f"Email Template: {request.email_template}\n"}) + "\n"
            
            logger.info(f"Starting process_data with industry: {request}")
            
            from dotenv import load_dotenv
            load_dotenv()

            # Initialize OpenAI client
            yield json.dumps({"status": "progress", "message": f"Initializing OpenAI client (t={int(time.time() - start_time)}s)"}) + "\n"
            logger.info("Initializing OpenAI client")
            openai_client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY")
            )
            cookie_dir = 'custom_lib/'

            if not hasattr(app.state, 'linkedin_client'):
                raise HTTPException(status_code=500, detail="LinkedIn client not initialized")
            
            # Use the client from app state
            linkedin_client = app.state.linkedin_client
            
            yield json.dumps({"status": "progress", "message": f"Starting profile enrichment (t={int(time.time() - start_time)}s)"}) + "\n"
            logger.info(f"Enriching user profile: {request.user_linkedin_url}")
            user_profile = enrich_person(
                linkedin=linkedin_client,
                value=request.user_linkedin_url,
                url_value=True
            )
            
            # Parse CSV data
            logger.info("Parsing CSV data")
            csv_reader = csv.reader(StringIO(request.csv_data))
            csv_data_list = [row for row in csv_reader]
            
            # Get the URNs (first column)
            list_of_urls = [row[3] for row in csv_data_list[1:]]  # Skip header
            
            yield json.dumps({"status": "progress", "message": f"Found {len(list_of_urls)} URLs to process, splitting between 1 client(s) (t={int(time.time() - start_time)}s)"}) + "\n"
            logger.info(f"Found {len(list_of_urls)} URLs to process, splitting {len(list_of_urls)} between clients")
            
            # Create async tasks for both clients
            logger.info("Starting parallel profile enrichment with both clients")
            
            async def process_client(client, urls, client_name, start_time):
                results = multi_enrich_persons(
                    linkedin=client,
                    values=urls,
                    url_value=True
                )
                yield json.dumps({"status": "progress", "message": f"{client_name} enriched {len(results)} profiles (t={int(time.time() - start_time)}s)"}) + "\n"
                yield results  # Yield the results as the last item
            
            # Process URLs with first client
            logger.info("Starting profile enrichment with client")
            multi_result_enriched = None
            async for item in process_client(linkedin_client, list_of_urls, "Client 1", start_time):
                if isinstance(item, str):  # If it's a progress message
                    yield item
                else:  # If it's the results
                    multi_result_enriched = item
            
            yield json.dumps({"status": "progress", "message": f"Successfully enriched {len(multi_result_enriched)} profiles (t={int(time.time() - start_time)}s)"}) + "\n"
            
            # Send checkpoint before email drafting
            yield json.dumps({"status": "drafting", "message": f"Starting email drafting (t={int(time.time() - start_time)}s)"}) + "\n"
            
            # Process emails using batch processing
            logger.info("Starting batch email drafting")
            
            all_emails = []
            total_profiles = len(multi_result_enriched)
            batch_size = 10
            
            for i in range(0, total_profiles, batch_size):
                batch = multi_result_enriched[i:i + batch_size]
                current_batch_size = len(batch)
                logger.info(f"Processing batch {i//batch_size + 1} with {current_batch_size} profiles")
                yield json.dumps({
                    "status": "progress", 
                    "message": f"Processing email batch {i//batch_size + 1}/{(total_profiles + batch_size - 1)//batch_size} (t={int(time.time() - start_time)}s)"
                }) + "\n"
                
                # Create tasks for the batch
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
                        Role: {request.keyword_industry}
                        Email template:
                        {request.email_template}
                        """}
                    ]
                    
                    tasks.append(
                        openai_client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=messages,
                            temperature=0.3,
                            max_tokens=500
                        )
                    )
                
                # Process batch concurrently
                batch_responses = await asyncio.gather(*tasks)
                batch_emails = [response.choices[0].message.content for response in batch_responses]
                all_emails.extend(batch_emails)
                
                logger.info(f"Completed batch {i//batch_size + 1}, total emails: {len(all_emails)}/{total_profiles}")
                yield json.dumps({
                    "status": "progress",
                    "message": f"Completed {len(all_emails)}/{total_profiles} emails (t={int(time.time() - start_time)}s)"
                }) + "\n"
            
            emails = all_emails
            
            # Send checkpoint before email drafting
            yield json.dumps({"status": "drafting", "message": f"Adding enriched data to CSV (t={int(time.time() - start_time)}s)"}) + "\n"
            
            # Add enriched data to CSV
            logger.info("Adding enriched data to CSV")
            for i in range(len(csv_data_list[1:])):  # Skip header
                email_data = emails[i]
                csv_data_list[i+1][6] = email_data
            
            yield json.dumps({"status": "drafting", "message": f"Preparing final CSV (t={int(time.time() - start_time)}s)"}) + "\n"
            
            # Prepare final CSV response
            output_csv = StringIO()
            csv_writer = csv.writer(output_csv)
            csv_writer.writerows(csv_data_list)
            
            # Send final CSV data
            yield json.dumps({
                "status": "completed",
                "message": f"Process completed (t={int(time.time() - start_time)}s)",
                "csv_data": output_csv.getvalue()
            }) + "\n"
            
        except Exception as e:
            logger.error(f"Error in process_data: {str(e)}", exc_info=True)
            yield json.dumps({
                "status": "error",
                "message": f"Error (t={int(time.time() - start_time)}s): {str(e)}"
            }) + "\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream"
    )

@app.get("/")
async def root():
    return {"message": "AutoMail AI API is running"}
