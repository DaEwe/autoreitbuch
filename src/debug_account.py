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

print("Fetching myaccount.php...")
response = client.client.get("/myaccount.php")
html = response.text

soup = BeautifulSoup(html, 'html.parser')

print("\n--- TABLES FOUND ---")
tables = soup.find_all('table')
for i, table in enumerate(tables):
    print(f"\nTable #{i}:")
    # Print headers
    headers = [th.get_text(strip=True) for th in table.find_all('th')]
    print(f"Headers: {headers}")
    
    # Print ALL rows
    rows = table.find_all('tr')
    for j, tr in enumerate(rows):
        cols = [td.get_text(strip=True) for td in tr.find_all('td')]
        if cols:
            print(f"Row {j}: {cols}")

print("\n--- HEADINGS ---")
for h in soup.find_all(['h3', 'h4']):
    print(h.get_text(strip=True))
