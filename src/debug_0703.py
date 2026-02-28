import os
import sys
from client import ReitbuchClient
from datetime import date, datetime, timedelta
import re

username = os.environ.get("REITBUCH_USER")
password = os.environ.get("REITBUCH_PASSWORD")

client = ReitbuchClient()
if not client.login(username, password):
    print("Login failed")
    sys.exit(1)

target_date = datetime.strptime("07.03.2026", "%d.%m.%Y").date()
today = date.today()

# Week offset
start_of_current_week = today - timedelta(days=today.weekday())
start_of_target_week = target_date - timedelta(days=target_date.weekday())
week_diff = (start_of_target_week - start_of_current_week).days // 7

print(f"Fetching week offset: {week_diff}")
html = client.get_weekly_plan(week_diff)

from bs4 import BeautifulSoup

# ... imports ...

# ... after fetching html ...

soup = BeautifulSoup(html, 'html.parser')
day_div = soup.find("div", id="collapse2026-03-07")

if day_div:
    print("\n--- CONTENT OF 07.03.2026 ---")
    events = day_div.find_all("div", class_="wp_event")
    
    # Get loginuid
    match = re.search(r'id="loginuid" name="loginuid" value="(\d+)"', html)
    loginuid = match.group(1) if match else "0"
    print(f"LoginUID: {loginuid}")

    for event in events:
        text = event.find("div", class_="wp_text").get_text(strip=True)
        time = event.find("div", class_="wp_date").get_text(strip=True)
        
        # Extract ID
        onclick = event.get('onclick', '')
        # window.location.href='event.php?e=26944';
        eid = ''
        if 'e=' in onclick:
            eid = onclick.split('e=')[1].split("'")[0]
            
        print(f"[{time}] {text} (ID: {eid})")
        
        if "Dressur Standard" in text and "09:00" in time:
            print(f"--> FOUND TARGET! Checking details for ID {eid}...")
            
            params = {"loginuid": loginuid, "step": "PRE", "next": "", "eventid": eid, "courseid": "0"}
            try:
                # Use client method if available or manual post
                # We need to use 'client' object from script scope
                # But client object is ReitbuchClient instance.
                # Accessing internal client for raw request? No, use ajax_request method.
                resp = client.ajax_request("ax.checkin.showcheckin", params)
                print("--- AJAX RESPONSE ---")
                print(resp)
                print("---------------------")
            except Exception as e:
                print(f"Error checking details: {e}")
else:
    print("No collapse2026-03-07 found!")


