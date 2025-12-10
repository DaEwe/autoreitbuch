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
                if parent.get('id', '').startswith('col_'): # Common pattern?
                     date_context = parent.get('id')
                     break
                # Check for day headers
                # Use a specific attribute if found
                # Reitbuch often uses id="day_YYYY-MM-DD" or similar
                
                # Check siblings or previous elements?
                # Let's just grab the 'id' of the parent for now to see.
                if parent.get('id'):
                    pass # Keep looking up
                
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
                # 'date_context': date_context # Add this dry run
            })
            
    return lessons

