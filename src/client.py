import httpx
import logging

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
            timeout=30.0
        )

    def login(self, username, password):
        """
        Logs into the application.
        The login flow appears to be:
        1. Access the main page/login page to get a session cookie (optional but good practice).
        2. POST credentials to /weekplan.php (based on the user's curl command).
        """
        logger.info(f"Attempting login for user: {username}")
        
        # Step 1: Browse to root to initialize session/cookies
        try:
            # We hit index.php or similar first to get a PHPSESSID if strictly needed,
            # but often we can just post. Let's try to just hit the root first.
            self.client.get("/")
        except httpx.RequestError as e:
            logger.error(f"Network error during initial connection: {e}")
            raise

        # Step 2: POST login data
        # Based on user's curl:
        # endpoint: weekplan.php
        # data: loginuser=...&loginpwd=...&loginsubmit=X...
        
        # We need to grab the current PHPSESSID if it exists to send it in the body 
        # as 'loginsid' if that's required by the backend, though usually cookies handle it.
        # The curl command had 'loginsid' matching the cookie.
        
        cookies = self.client.cookies
        phpsessid = cookies.get("PHPSESSID", "")
        
        data = {
            "loginuser": username,
            "loginpwd": password,
            "loginsubmit": "X",
            "loginscrwidth": "1920",
            "loginscrheight": "1080",
            "loginuid": "0",
            "loginsid": phpsessid, # Reflecting the session ID if we have it
            "loginconfirm": ""
        }
        
        response = self.client.post("/weekplan.php", data=data)
        
        if response.status_code != 200:
            logger.error(f"Login request failed with status code: {response.status_code}")
            return False

        # Basic verification: Check if we are still on the login page or redirected/content changed.
        # usually successful login will show the week plan or "Logout" button.
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
