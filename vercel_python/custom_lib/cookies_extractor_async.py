from requests.cookies import RequestsCookieJar, create_cookie
import logging

logger = logging.getLogger(__name__)

def cookie_extractor_from_json(cookies_json: dict) -> RequestsCookieJar:
    """
    Creates a cookie jar from JSON cookie data for LinkedIn API use.
    
    Args:
        cookies_json (dict): JSON cookie data in EditThisCookie format
    
    Returns:
        RequestsCookieJar: Cookie jar ready to use with LinkedIn API
    """
    try:
        cookie_jar = RequestsCookieJar()

        for cookie_data in cookies_json:
            cookie = create_cookie(
                domain=cookie_data["domain"],
                name=cookie_data["name"],
                value=cookie_data["value"],
                path=cookie_data["path"],
                secure=cookie_data["secure"],
                expires=cookie_data.get("expirationDate", None),
                rest={
                    "HttpOnly": cookie_data.get("httpOnly", False),
                    "SameSite": cookie_data.get("sameSite", "unspecified"),
                    "HostOnly": cookie_data.get("hostOnly", False),
                }
            )
            cookie_jar.set_cookie(cookie)
        
        logger.info(f"Successfully created cookie jar with {len(cookies_json)} cookies")
        return cookie_jar

    except Exception as e:
        logger.error(f"Failed to process cookies: {str(e)}")
        raise