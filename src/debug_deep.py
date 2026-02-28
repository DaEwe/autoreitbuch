import os
import sys
from client import ReitbuchClient
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta

username = os.environ.get("REITBUCH_USER")
password = os.environ.get("REITBUCH_PASSWORD")

client = ReitbuchClient()
if not client.login(username, password):
    print("Login failed")
    sys.exit(1)

# 1. Dump Account
print("\n=== MY ACCOUNT ===")
resp = client.client.get("/myaccount.php")
with open("debug_account.html", "w") as f:
    f.write(resp.text)
# Print table rows
soup = BeautifulSoup(resp.text, 'html.parser')
tables = soup.find_all('table')
for i, table in enumerate(tables):
    print(f"Table {i}:")
    for tr in table.find_all('tr'):
        print([td.get_text(strip=True) for td in tr.find_all(['td', 'th'])])

# 2. Dump Weekplan 28.02.
print("\n=== WEEKPLAN 28.02. ===")
target_date = datetime.strptime("28.02.2026", "%d.%m.%Y").date()
# Calculate offset (simplified logic)
# 28.02. is in 3 weeks from today (08.02.)?
# 08.02. (Sun) -> Week 0 ends today.
# 09.02. (Mon) -> Week 1.
# ...
today = datetime.now().date()
start_current = today - timedelta(days=today.weekday())
start_target = target_date - timedelta(days=target_date.weekday())
week_diff = (start_target - start_current).days // 7
print(f"Week Offset: {week_diff}")

html = client.get_weekly_plan(week_diff)
with open("debug_weekplan.html", "w") as f:
    f.write(html)

soup = BeautifulSoup(html, 'html.parser')
# Find lesson
# ID for 28.02.?
# We search for "Dressur Standard" text
print("Scanning lessons...")
events = soup.find_all('div', class_='wp_event')
for ev in events:
    text = ev.get_text(separator='|', strip=True)
    if "Dressur Standard" in text and "09:00" in text:
        print(f"FOUND: {text}")
        onclick = ev.get('onclick')
        print(f"OnClick: {onclick}")
        # Get ID
        if 'e=' in onclick:
            eid = onclick.split('e=')[1].split("'")[0]
            print(f"ID: {eid}")
            
            # Check details
            # Get loginuid
            match = re.search(r'id="loginuid" name="loginuid" value="(\d+)"', html)
            loginuid = match.group(1) if match else "0"
            
            print("Checking details...")
            params = {"loginuid": loginuid, "step": "PRE", "next": "", "eventid": eid, "courseid": "0"}
            resp_pre = client.ajax_request("ax.checkin.showcheckin", params)
            print("--- AJAX RESPONSE ---")
            print(resp_pre)
            print("---------------------")
