import httpx
import logging
import re

logger = logging.getLogger(__name__)

class ReitbuchClient:
    def __init__(self, base_url="https://rfv-leonberg.reitbuch.com"):
        self.base_url = base_url
        self.client = httpx.Client(
            base_url=base_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Start-In-Task-Automation": "true" # Custom header to be nice
            },
            follow_redirects=True,
            timeout=60.0,
            verify=False
        )

    def login(self, username, password):
        """
        Logs into the application.
        Flow:
        1. GET /weekplan.php to get the login form and hidden 'loginsid'.
        2. POST credentials to /weekplan.php with the extracted sid.
        """
        logger.info(f"Attempting login for user: {username}")
        
        try:
            # Step 1: Get the login page to scrape the SID
            response_get = self.client.get("/weekplan.php")
            response_get.raise_for_status()
            html = response_get.text
            
            # Extract loginsid using regex
            # Look for <input ... id="loginsid" ... value="XYZ">
            match = re.search(r'id="loginsid"[^>]*value="([^"]+)"', html)
            if not match:
                # Try alternative order of attributes
                match = re.search(r'value="([^"]+)"[^>]*id="loginsid"', html)
            
            if match:
                loginsid = match.group(1)
                logger.debug(f"Extracted loginsid: {loginsid}")
            else:
                logger.warning("Could not extract loginsid from HTML. Falling back to cookie.")
                loginsid = self.client.cookies.get("PHPSESSID", "")

        except httpx.RequestError as e:
            logger.error(f"Network error during initial connection: {e}")
            raise

        # Step 2: POST login data
        data = {
            "loginuser": username,
            "loginpwd": password,
            "loginsubmit": "X",
            "loginscrwidth": "1920",
            "loginscrheight": "1080",
            "loginuid": "0",
            "loginsid": loginsid, 
            "loginconfirm": ""
        }
        
        response = self.client.post("/weekplan.php", data=data)
        
        if response.status_code != 200:
            logger.error(f"Login request failed with status code: {response.status_code}")
            return False

        # Basic verification
        text_lower = response.text.lower()
        if "logout" in text_lower or "abmelden" in text_lower:
            logger.info("Login successful (detected 'logout'/'abmelden' text).")
            return True
        elif 'id="loginform"' in text_lower or 'name="loginform"' in text_lower:
             logger.error("Login failed: Login form still present.")
             return False
        elif "falsches passwort" in text_lower or "user unknown" in text_lower:
             logger.error("Login failed: Invalid credentials.")
             return False
        
        # Fallback check
        logger.warning("Login status uncertain. Could not find explicit success/failure markers.")
        return True # Tentative success if no explicit failure
        
    def get_weekly_plan(self, week_offset=0):
        """
        Fetches the weekly plan page HTML. 
        week_offset: Integer representing the week offset from current week (0=current, 1=next, etc.)
        """
        params = {}
        if week_offset != 0:
            params['w'] = week_offset
            params['p'] = 1 # Seems to be required or standard
            
        response = self.client.get("/weekplan.php", params=params)
        response.raise_for_status()
        return response.text

    def get_event_details(self, event_id):
        """Fetches the event details page to find the booking form."""
        response = self.client.get(f"/event.php?e={event_id}")
        response.raise_for_status()
        return response.text

    def ajax_request(self, command, params, boxid="chkinbox"):
        """
        Sends an AJAX request to /ajax.php, mimicking rb_base.js.
        params should be a dict, which will be JSON encoded.
        """
        import json
        payload = {
            "command": command,
            "boxid": boxid,
            "params": json.dumps(params),
            "longtxt": ""
        }
        # The JS uses URLSearchParams which sends application/x-www-form-urlencoded
        response = self.client.post("/ajax.php", data=payload)
        response.raise_for_status()
        return response.text

    def get_event_details_ajax(self, event_id, login_uid):
        """
        Fetches the event details via AJAX to get the participant list.
        Corresponds to the 'ax.event.showeventdetails' command.
        """
        params = {
            "loginuid": str(login_uid),
            "eventid": str(event_id),
            "checkin": 0
        }
        return self.ajax_request("ax.event.showeventdetails", params, boxid="evt_detail")
