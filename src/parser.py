from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def parse_available_lessons(html_content):
    """
    Parses the weekplan HTML to find available lessons.
    
    Since we don't have the exact HTML structure yet, this is a best-effort 
    implementation that finds elements that look like lessons.
    
    Returns a list of dictionaries with lesson info.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    lessons = []
    
    # Heuristic: Look for elements that might be lessons.
    # Usually these are in a table or divs with specific classes.
    # We'll look for anything that looks 'bookable' or has time/date info.
    # This will need massive refinement once we see the real HTML.
    
    # For now, let's just log parsing attempts so the user can debug
    # logger.info("Parsing logic not fully implemented. dumping text for debugging.")
    
    links = soup.find_all('div', class_='wp_event')
    seen_ids = set()
    for link in links:
        # Extract onclick attribute for event ID
        onclick = link.get('onclick', '')
        # Expected format: "window.location.href='event.php?e=26094';"
        event_id = ''
        if 'event.php?e=' in onclick:
            try:
                event_id = onclick.split('e=')[1].split("'")[0]
            except IndexError:
                pass
        
        # Extract text details
        title = link.find('div', class_='wp_text')
        title = title.get_text(strip=True) if title else "Unknown"
        
        date_time = link.find('div', class_='wp_date')
        date_time = date_time.get_text(strip=True) if date_time else "Unknown"

        if event_id:
            # Check if it's in the past
            classes = link.get('class', [])
            is_bookable = 'wp_event_past' not in classes
            
            # Try to find date in parent hierarchy
            # Usually stricture is div key="2025-12-14" or similar
            date_context = "Unknown"
            parent = link.parent
            while parent and parent.name != 'body':
                parent_id = parent.get('id', '')
                if parent_id.startswith('collapse'): 
                     # ID format: collapse2025-12-20
                     # Extract everything after 'collapse'
                     possible_date = parent_id.replace('collapse', '')
                     # Simple validation: checks if it looks like a date (roughly)
                     if len(possible_date) >= 10: 
                        date_context = possible_date
                        break
                
                # Also check for col_ just in case
                if parent_id.startswith('col_'):
                     date_context = parent_id
                     break

                parent = parent.parent
            
            # Re-attempt: Look for the specific 'day' data attribute often found in these tables
            # or just look for 'headingYYYY-MM-DD' above it?
            
            if event_id in seen_ids:
                continue
            seen_ids.add(event_id)

            lessons.append({
                'id': event_id,
                'title': title,
                'time': date_time,
                'is_bookable': is_bookable,
                'raw_onclick': onclick,
                'date_context': date_context
            })
            
    return lessons


def parse_participants(html_content):
    """
    Parses the event details HTML to find participants and waiting list.
    Returns a dict with 'participants' and 'waiting_list' (lists of strings).
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    participants = []
    waiting_list = []
    
    # Heuristic: Look for headers like "Teilnehmer" or "Warteliste"
    # The structure is likely tables or lists following a header.
    
    
    # Strategy: Find all tables. Check their headers to identify if they are "Teilnehmer" or "Warteplätze".
    tables = soup.find_all('table')
    
    for table in tables:
        # Check header
        header_text = ""
        thead = table.find('thead')
        if not thead:
            continue
            
        th = thead.find('th')
        if not th:
            continue
            
        header_text = th.get_text(strip=True).lower()
        
        target_list = None
        if "teilnehmer" in header_text:
            target_list = participants
        elif "warteplätze" in header_text or "warteliste" in header_text:
            target_list = waiting_list
            
        if target_list is None:
            continue
            
        # Parse body
        tbody = table.find('tbody')
        if not tbody:
            continue
            
        for tr in tbody.find_all('tr'):
            tds = tr.find_all('td')
            if not tds:
                continue
                
            # Name is usually in the first column
            name_cell = tds[0]
            # Use separator to keep space between badge (number) and name
            name_text = name_cell.get_text(separator=' ', strip=True)
            
            # Filter out "(frei)" slots
            if "(frei)" in name_text:
                continue
                
            # Format: "1 Elena X." -> Clean up if needed, but keeping the number is informative.
            # actually, let's keep it simple.
            # The span contains the number. The text node contains the name.
            # "1 Elena X." is returned by get_text().
            
            target_list.append(name_text)

    return {
        "participants": participants,
        "waiting_list": waiting_list
    }

