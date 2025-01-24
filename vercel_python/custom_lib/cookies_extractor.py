from requests.cookies import RequestsCookieJar, create_cookie
from linkedin_api.cookie_repository import CookieRepository
import json

# C:\Users\adamh\.linkedin_api\cookies

def cookie_extractor():

    cookies = json.load(open('custom_lib/cookies.json')) # Path of exported cookie via https://www.editthiscookie.com/

    cookie_jar = RequestsCookieJar()

    for cookie_data in cookies:
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


    new_repo = CookieRepository() # can adjust the cookie path here ...
    # new_repo.save(cookie_jar, 'email_or_username')
    new_repo.save(cookie_jar, 'productionadamh@gmail.com')

    return new_repo

if __name__ == "__main__":
    cookie_extractor()
