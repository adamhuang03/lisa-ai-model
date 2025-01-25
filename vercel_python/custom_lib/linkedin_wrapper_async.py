from typing import List, Dict, Optional, Union, Literal
from linkedin_api import Linkedin as BaseLinkedin
from operator import itemgetter
from linkedin_api.utils.helpers import get_id_from_urn, get_urn_from_raw_update 
from asyncio import sleep
import random
import aiohttp
import logging
import json
from bs4 import BeautifulSoup, Tag
from http.cookies import SimpleCookie
from typing import Optional, Dict
from custom_lib.cookies_extractor_async import CookieRepository
from requests.cookies import RequestsCookieJar

def default_evade_async():
    """
    A catch-all method to try and evade suspension from Linkedin.
    Currenly, just delays the request by a random (bounded) time
    """
    logger.debug("Evading suspension...")
    sleep(random.randint(2, 5)) 

logger = logging.getLogger(__name__)

class UnauthorizedException(Exception):
    pass

class ChallengeException(Exception):
    pass

class ClientAsync:
    """
    Async class to act as a client for the Linkedin API.
    """

    # Settings for general Linkedin API calls
    LINKEDIN_BASE_URL = "https://www.linkedin.com"
    API_BASE_URL = f"{LINKEDIN_BASE_URL}/voyager/api"
    REQUEST_HEADERS = {
        "user-agent": " ".join(
            [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5)",
                "AppleWebKit/537.36 (KHTML, like Gecko)",
                "Chrome/83.0.4103.116 Safari/537.36",
            ]
        ),
        "accept-language": "en-AU,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "x-li-lang": "en_US",
        "x-restli-protocol-version": "2.0.0",
    }

    # Settings for authenticating with Linkedin
    AUTH_REQUEST_HEADERS = {
        "X-Li-User-Agent": "LIAuthLibrary:0.0.3 com.linkedin.android:4.1.881 Asus_ASUS_Z01QD:android_9",
        "User-Agent": "ANDROID OS",
        "X-User-Language": "en",
        "X-User-Locale": "en_US",
        "Accept-Language": "en-us",
    }

    def __init__(
        self, *, debug=False, refresh_cookies=False, proxies={}, cookies_dir: str = ""
    ):
        self.session: Optional[aiohttp.ClientSession] = None
        self.proxies = proxies
        self.logger = logger
        self.metadata = {}
        self._use_cookie_cache = not refresh_cookies
        self._cookie_repository = CookieRepository(cookies_dir=cookies_dir)
        self._cookies = None
        
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)

    async def __aenter__(self):
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.REQUEST_HEADERS)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None

    async def _request_session_cookies(self) -> Dict[str, str]:
        """
        Return a new set of session cookies as given by Linkedin.
        """
        self.logger.debug("Requesting new cookies.")
        
        async with aiohttp.ClientSession(headers=self.AUTH_REQUEST_HEADERS) as session:
            async with session.get(
                f"{self.LINKEDIN_BASE_URL}/uas/authenticate",
                proxy=self.proxies.get('https') if self.proxies else None
            ) as response:
                cookies = response.cookies
                return {key: morsel.value for key, morsel in cookies.items()}

    def _set_session_cookies(self, cookies: Dict[str, str]):
        """
        Set cookies of the current session.
        """
        self._cookies = cookies
        if self.session:
            self.session._cookie_jar.update_cookies(cookies)
            if 'JSESSIONID' in cookies:
                self.session._default_headers["csrf-token"] = cookies["JSESSIONID"].strip('"')

    @property
    def cookies(self):
        return self._cookies

    async def authenticate(self, username: str, password: str):
        if self._use_cookie_cache:
            self.logger.debug("Attempting to use cached cookies")
            cookies = self._cookie_repository.get(username)
            if cookies:
                self.logger.debug("Using cached cookies")
                self._set_session_cookies(cookies)
                await self._fetch_metadata()
                return

        await self._do_authentication_request(username, password)
        await self._fetch_metadata()

    async def _fetch_metadata(self):
        """
        Get metadata about the "instance" of the LinkedIn application.
        """
        async with aiohttp.ClientSession(headers=self.AUTH_REQUEST_HEADERS, cookies=self._cookies) as session:
            async with session.get(
                f"{self.LINKEDIN_BASE_URL}",
                proxy=self.proxies.get('https') if self.proxies else None
            ) as response:
                text = await response.text()
                
                soup = BeautifulSoup(text, "lxml")

                clientApplicationInstanceRaw = soup.find(
                    "meta", attrs={"name": "applicationInstance"}
                )
                if clientApplicationInstanceRaw and isinstance(
                    clientApplicationInstanceRaw, Tag
                ):
                    clientApplicationInstanceRaw = clientApplicationInstanceRaw.attrs.get(
                        "content", {}
                    )
                    clientApplicationInstance = json.loads(clientApplicationInstanceRaw)
                    self.metadata["clientApplicationInstance"] = clientApplicationInstance

                clientPageInstanceIdRaw = soup.find(
                    "meta", attrs={"name": "clientPageInstanceId"}
                )
                if clientPageInstanceIdRaw and isinstance(clientPageInstanceIdRaw, Tag):
                    clientPageInstanceId = clientPageInstanceIdRaw.attrs.get("content", {})
                    self.metadata["clientPageInstanceId"] = clientPageInstanceId

    async def _do_authentication_request(self, username: str, password: str):
        """
        Authenticate with Linkedin asynchronously.
        """
        cookies = await self._request_session_cookies()
        self._set_session_cookies(cookies)

        payload = {
            "session_key": username,
            "session_password": password,
            "JSESSIONID": cookies["JSESSIONID"],
        }

        async with aiohttp.ClientSession(headers=self.AUTH_REQUEST_HEADERS, cookies=cookies) as session:
            async with session.post(
                f"{self.LINKEDIN_BASE_URL}/uas/authenticate",
                data=payload,
                proxy=self.proxies.get('https') if self.proxies else None
            ) as response:
                try:
                    data = await response.json()
                except:
                    data = {}

                if response.status == 401:
                    print(f"Request failed with status {response.status}")
                    print(f"Response content: {await response.text()}")
                    raise UnauthorizedException()

                if response.status != 200:
                    print(f"Request failed with status {response.status}")
                    print(f"Response content: {await response.text()}")
                    raise Exception()

                if data and data.get("login_result") != "PASS":
                    print(f"Request failed with status {response.status}")
                    print(f"Response content: {await response.text()}")
                    raise ChallengeException(data.get("login_result"))

                response_cookies = {key: morsel.value for key, morsel in response.cookies.items()}
                self._set_session_cookies(response_cookies)
                self._cookie_repository.save(response_cookies, username)


class LinkedinWrapperAsync(BaseLinkedin):
    def __init__(self, username, password, *, authenticate=True, refresh_cookies=False, debug=False, proxies={}, cookies=None, cookies_dir: str = ""):
        super().__init__(username, password, authenticate=authenticate, refresh_cookies=refresh_cookies, debug=debug, proxies=proxies, cookies=cookies, cookies_dir=cookies_dir)
        self.client = ClientAsync(
            refresh_cookies=refresh_cookies,
            debug=debug,
            proxies=proxies,
            cookies_dir=cookies_dir,
        )
    
    def search_geo(self, keywords: str, **kwargs) -> List[Dict]:
        """Search for geographic locations on LinkedIn.
        
        Args:
            keywords: Search term for location
            **kwargs: Additional parameters to pass to request
        
        Returns:
            List of location results with their details
        """
        
        # Convert params to the format expected by the API
        formatted_params = f"(keywords:{keywords},query:(typeaheadFilterQuery:(geoSearchTypes:List(MARKET_AREA,COUNTRY_REGION,ADMIN_DIVISION_1,CITY))),type:GEO)"
        
        uri = f"/graphql?variables={formatted_params}&queryId=voyagerSearchDashReusableTypeahead.54529a68d290553c6f24e28ab3448654"
        
        res = self._fetch(uri, headers={"accept": "application/vnd.linkedin.normalized+json+2.1"})
        data = res.json()

        with open('test.json', 'w') as f:
            import json
            json.dump(data, f, indent=4)

        if "included" not in data:
            return []
            
        results = []
        first_location = data\
            .get("data", [])\
            .get("data", [])\
            .get("searchDashReusableTypeaheadByType", [])['elements'][0]
        geo_urn = get_id_from_urn(first_location['trackingUrn'])
        
        return geo_urn
    
    def search_people(
        self,
        keywords: Optional[str] = None,
        connection_of: Optional[str] = None,
        network_depths: Optional[
            List[Union[Literal["F"], Literal["S"], Literal["O"]]]
        ] = None,
        current_company: Optional[List[str]] = None,
        past_companies: Optional[List[str]] = None,
        or_past_companies: bool = False,
        nonprofit_interests: Optional[List[str]] = None,
        profile_languages: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        industries: Optional[List[str]] = None,
        schools: Optional[List[str]] = None,
        or_schools: bool = False,
        contact_interests: Optional[List[str]] = None,
        service_categories: Optional[List[str]] = None,
        include_private_profiles=False,  # profiles without a public id, "Linkedin Member"
        # Keywords filter
        keyword_first_name: Optional[str] = None,
        keyword_last_name: Optional[str] = None,
        # `keyword_title` and `title` are the same. We kept `title` for backward compatibility. Please only use one of them.
        keyword_title: Optional[str] = None,
        keyword_company: Optional[str] = None,
        keyword_school: Optional[str] = None,
        network_depth: Optional[
            Union[Literal["F"], Literal["S"], Literal["O"]]
        ] = None,  # DEPRECATED - use network_depths
        title: Optional[str] = None,  # DEPRECATED - use keyword_title
        **kwargs,
    ) -> List[Dict]:
        """Perform a LinkedIn search for people.

        :param keywords: Keywords to search on
        :type keywords: str, optional
        :param current_company: A list of company URN IDs (str)
        :type current_company: list, optional
        :param past_companies: A list of company URN IDs (str)
        :type past_companies: list, optional
        :param or_past_companies: Boolean to determine if you want to search for profiles with any of the companies in the list
        :type or_past_companies: bool, optional
        :param regions: A list of geo URN IDs (str)
        :type regions: list, optional
        :param industries: A list of industry URN IDs (str)
        :type industries: list, optional
        :param schools: A list of school URN IDs (str)
        :type schools: list, optional
        :param or_schools: Boolean to determine if you want to search for profiles with any of the schools in the list
        :type or_schools: bool, optional
        :param profile_languages: A list of 2-letter language codes (str)
        :type profile_languages: list, optional
        :param contact_interests: A list containing one or both of "proBono" and "boardMember"
        :type contact_interests: list, optional
        :param service_categories: A list of service category URN IDs (str)
        :type service_categories: list, optional
        :param network_depth: Deprecated, use `network_depths`. One of "F", "S" and "O" (first, second and third+ respectively)
        :type network_depth: str, optional
        :param network_depths: A list containing one or many of "F", "S" and "O" (first, second and third+ respectively)
        :type network_depths: list, optional
        :param include_private_profiles: Include private profiles in search results. If False, only public profiles are included. Defaults to False
        :type include_private_profiles: boolean, optional
        :param keyword_first_name: First name
        :type keyword_first_name: str, optional
        :param keyword_last_name: Last name
        :type keyword_last_name: str, optional
        :param keyword_title: Job title
        :type keyword_title: str, optional
        :param keyword_company: Company name
        :type keyword_company: str, optional
        :param keyword_school: School name
        :type keyword_school: str, optional
        :param connection_of: Connection of LinkedIn user, given by profile URN ID
        :type connection_of: str, optional
        :param limit: Maximum length of the returned list, defaults to -1 (no limit)
        :type limit: int, optional

        :return: List of profiles (minimal data only)
        :rtype: list
        """
        filters = ["(key:resultType,value:List(PEOPLE))"]
        if connection_of:
            filters.append(f"(key:connectionOf,value:List({connection_of}))")
        if network_depths:
            stringify = " | ".join(network_depths)
            filters.append(f"(key:network,value:List({stringify}))")
        elif network_depth:
            filters.append(f"(key:network,value:List({network_depth}))")
        if regions:
            stringify = " | ".join(regions)
            filters.append(f"(key:geoUrn,value:List({stringify}))")
        if industries:
            stringify = " | ".join(industries)
            filters.append(f"(key:industry,value:List({stringify}))")
        if current_company:
            stringify = " | ".join(current_company)
            filters.append(f"(key:currentCompany,value:List({stringify}))")
        if past_companies:
            if or_past_companies:
                stringify = ",".join(past_companies)
            else:
                stringify = " | ".join(past_companies)
            filters.append(f"(key:pastCompany,value:List({stringify}))")
        if profile_languages:
            stringify = " | ".join(profile_languages)
            filters.append(f"(key:profileLanguage,value:List({stringify}))")
        if nonprofit_interests:
            stringify = " | ".join(nonprofit_interests)
            filters.append(f"(key:nonprofitInterest,value:List({stringify}))")
        if schools:
            if or_schools:
                stringify = ",".join(schools)
            else:
                stringify = " | ".join(schools)
            filters.append(f"(key:schoolFilter,value:List({stringify}))")
        if service_categories:
            stringify = " | ".join(service_categories)
            filters.append(f"(key:serviceCategory,value:List({stringify}))")
        # `Keywords` filter
        keyword_title = keyword_title if keyword_title else title
        if keyword_first_name:
            filters.append(f"(key:firstName,value:List({keyword_first_name}))")
        if keyword_last_name:
            filters.append(f"(key:lastName,value:List({keyword_last_name}))")
        if keyword_title:
            filters.append(f"(key:title,value:List({keyword_title}))")
        if keyword_company:
            filters.append(f"(key:company,value:List({keyword_company}))")
        if keyword_school:
            filters.append(f"(key:school,value:List({keyword_school}))")

        params = {"filters": "List({})".format(",".join(filters))}

        if keywords:
            params["keywords"] = keywords

        data = self.search(params, **kwargs)

        results = []
        from pprint import pprint
        for item in data:
            if (
                not include_private_profiles
                and (item.get("entityCustomTrackingInfo") or {}).get(
                    "memberDistance", None
                )
                == "OUT_OF_NETWORK"
            ):
                continue
            # results.append(item)
            results.append(
                {
                    "urn_id": get_id_from_urn(
                        get_urn_from_raw_update(item.get("entityUrn", None))
                    ),
                    "distance": (item.get("entityCustomTrackingInfo") or {}).get(
                        "memberDistance", None
                    ),
                    "jobtitle": (item.get("primarySubtitle") or {}).get("text", None),
                    "location": (item.get("secondarySubtitle") or {}).get("text", None),
                    "name": (item.get("title") or {}).get("text", None),
                    "url": item.get("navigationUrl", None),
                }
            )

        return results

    def get_profile_async(
        self, public_id: Optional[str] = None, urn_id: Optional[str] = None
    ) -> Dict:
        """Fetch data for a given LinkedIn profile.

        :param public_id: LinkedIn public ID for a profile
        :type public_id: str, optional
        :param urn_id: LinkedIn URN ID for a profile
        :type urn_id: str, optional

        :return: Profile data
        :rtype: dict
        """
        # NOTE this still works for now, but will probably eventually have to be converted to
        # https://www.linkedin.com/voyager/api/identity/profiles/ACoAAAKT9JQBsH7LwKaE9Myay9WcX8OVGuDq9Uw
        res = self._fetch(f"/identity/profiles/{public_id or urn_id}/profileView")

        data = res.json()

        if data and "status" in data and data["status"] != 200:
            self.logger.info("request failed with status %d", data["status"])
            return {}

        # massage [profile] data
        profile = data["profile"]
        if "miniProfile" in profile:
            if "picture" in profile["miniProfile"]:
                profile["displayPictureUrl"] = profile["miniProfile"]["picture"][
                    "com.linkedin.common.VectorImage"
                ]["rootUrl"]

                images_data = profile["miniProfile"]["picture"][
                    "com.linkedin.common.VectorImage"
                ]["artifacts"]
                for img in images_data:
                    w, h, url_segment = itemgetter(
                        "width", "height", "fileIdentifyingUrlPathSegment"
                    )(img)
                    profile[f"img_{w}_{h}"] = url_segment

            profile["profile_id"] = get_id_from_urn(profile["miniProfile"]["entityUrn"])
            profile["profile_urn"] = profile["miniProfile"]["entityUrn"]
            profile["member_urn"] = profile["miniProfile"]["objectUrn"]
            profile["public_id"] = profile["miniProfile"]["publicIdentifier"]

            del profile["miniProfile"]

        del profile["defaultLocale"]
        del profile["supportedLocales"]
        del profile["versionTag"]
        del profile["showEducationOnProfileTopCard"]

        # massage [experience] data
        experience = data["positionView"]["elements"]
        for item in experience:
            if "company" in item and "miniCompany" in item["company"]:
                if "logo" in item["company"]["miniCompany"]:
                    logo = item["company"]["miniCompany"]["logo"].get(
                        "com.linkedin.common.VectorImage"
                    )
                    if logo:
                        item["companyLogoUrl"] = logo["rootUrl"]
                del item["company"]["miniCompany"]

        profile["experience"] = experience

        # massage experience position data
        enriched_experiences = data["positionGroupView"]["elements"]
        processed_experience = []
        
        for experience in enriched_experiences:
            if "miniCompany" in experience:
                company_name = experience.get("name", "")
                company_public_id = experience.get("miniCompany", {}).get("universalName", "")
            
                # Process each position within the company
                for position in experience.get("positions", []):
                    experience_entry = {
                        "title": position.get("title", "No title available"),
                        "companyName": company_name,
                        "companyPublicId": company_public_id,
                        "description": position.get("description", "No description available"),
                        "startDate": None,
                        "endDate": None
                    }
                
                # Extract dates     
                time_period = position.get("timePeriod", {})
                if "startDate" in time_period:
                    experience_entry["startDate"] = time_period["startDate"]
                if "endDate" in time_period:
                    experience_entry["endDate"] = time_period["endDate"]
                    
                # Get company logo if available
                if "company" in position and "miniCompany" in position["company"]:
                    if "logo" in position["company"]["miniCompany"]:
                        logo = position["company"]["miniCompany"]["logo"].get(
                            "com.linkedin.common.VectorImage"
                        )
                        if logo:
                            experience_entry["companyLogoUrl"] = logo["rootUrl"]
                    
                processed_experience.append(experience_entry)
        
        profile["experience"] = processed_experience

        # massage [education] data
        education = data["educationView"]["elements"]
        for item in education:
            if "school" in item:
                if "logo" in item["school"]:
                    item["school"]["logoUrl"] = item["school"]["logo"][
                        "com.linkedin.common.VectorImage"
                    ]["rootUrl"]
                    del item["school"]["logo"]

        profile["education"] = education

        # massage [languages] data
        languages = data["languageView"]["elements"]
        for item in languages:
            del item["entityUrn"]
        profile["languages"] = languages

        # massage [publications] data
        publications = data["publicationView"]["elements"]
        for item in publications:
            del item["entityUrn"]
            for author in item.get("authors", []):
                del author["entityUrn"]
        profile["publications"] = publications

        # massage [certifications] data
        certifications = data["certificationView"]["elements"]
        for item in certifications:
            del item["entityUrn"]
        profile["certifications"] = certifications

        # massage [volunteer] data
        volunteer = data["volunteerExperienceView"]["elements"]
        for item in volunteer:
            del item["entityUrn"]
        profile["volunteer"] = volunteer

        # massage [honors] data
        honors = data["honorView"]["elements"]
        for item in honors:
            del item["entityUrn"]
        profile["honors"] = honors

        # massage [projects] data
        projects = data["projectView"]["elements"]
        for item in projects:
            del item["entityUrn"]
        profile["projects"] = projects
        # massage [skills] data
        skills = data["skillView"]["elements"]
        for item in skills:
            del item["entityUrn"]
        profile["skills"] = skills

        profile["urn_id"] = profile["entityUrn"].replace("urn:li:fs_profile:", "")

        return profile

    def _fetch(self, uri: str, evade=default_evade_async, base_request=False, **kwargs):
        """GET request to Linkedin API"""
        evade()

        url = f"{self.client.API_BASE_URL if not base_request else self.client.LINKEDIN_BASE_URL}{uri}"
        return self.client.session.get(url, **kwargs)

if __name__ == "__main__":
    test = get_id_from_urn("urn:li:fs_normalized_company:3660")
    print(test)