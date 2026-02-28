import os
import sys
from client import ReitbuchClient
from bs4 import BeautifulSoup

username = os.environ.get("REITBUCH_USER")
password = os.environ.get("REITBUCH_PASSWORD")

client = ReitbuchClient()
if not client.login(username, password):
    print("Login failed")
    sys.exit(1)

print("Fetching weekplan...")
html = client.get_weekly_plan(0)
soup = BeautifulSoup(html, 'html.parser')

print("\n--- LINKS FOUND ---")
for a in soup.find_all('a'):
    href = a.get('href')
    text = a.get_text(strip=True)
    if href and text:
        print(f"Text: '{text}' -> Link: '{href}'")

print("\n--- BUTTONS FOUND ---")
for btn in soup.find_all('button'):
    text = btn.get_text(strip=True)
    onclick = btn.get('onclick')
    name = btn.get('name')
    print(f"Btn: '{text}' (Name: {name}) -> OnClick: {onclick}")
