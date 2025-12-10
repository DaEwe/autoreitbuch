import os
import sys
import logging
from client import ReitbuchClient
from parser import parse_available_lessons

# Configure logging
logging.basicConfig(
    level=logging.WARNING, # Default to WARNING to suppress libraries
    format='%(message)s'   # Concise format
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Keep our logger at INFO

# Silence specific noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("parser").setLevel(logging.WARNING)

def main():
    username = os.environ.get("REITBUCH_USER")
    password = os.environ.get("REITBUCH_PASSWORD")

    if not username or not password:
        logger.error("Error: REITBUCH_USER and REITBUCH_PASSWORD environment variables must be set.")
        sys.exit(1)

    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description='Automate Reitbuch booking.')
    parser.add_argument('--book', action='store_true', help='Actually perform the booking (default is dry-run)')
    parser.add_argument('--date', type=str, help='Specific date to check (DD.MM.YYYY)')
    args = parser.parse_args()

    client = ReitbuchClient()

    try:
        if not client.login(username, password):
            logger.error("Login failed. Check credentials.")
            sys.exit(1)
            
        logger.info("Login successful. Checking schedule for 'Dressur Standard' (09:00 - 10:00)...")
        print("-" * 60)
        print(f"{'Date':<15} | {'Lesson ID':<10} | {'Status':<30}")
        print("-" * 60)
        
        target_dates = []
        if args.date:
            from datetime import datetime
            try:
                dt = datetime.strptime(args.date, "%d.%m.%Y").date()
                target_dates = [dt]
            except ValueError:
                logger.error("Invalid date format. Please use DD.MM.YYYY")
                sys.exit(1)
        else:
            from datetime import date, timedelta
            today = date.today()
            days_ahead = 5 - today.weekday()
            if days_ahead <= 0: days_ahead += 7
            next_saturday = today + timedelta(days=days_ahead)
            target_dates = [next_saturday + timedelta(weeks=i) for i in range(4)] 
        
        target_found = False
        
        for target_date in target_dates:
            date_str = target_date.strftime("%d.%m.%Y")
            
            try:
                html = client.get_weekly_plan(date_str)
                lessons = parse_available_lessons(html)
                
                target_lessons = [l for l in lessons if "Dressur Standard" in l['title'] and "09:00" in l['time']]
                
                if not target_lessons:
                    print(f"{date_str:<15} | {'-':<10} | {'Not found':<30}")
                    continue

                for tl in target_lessons:
                    eid = tl['id']
                    status_msg = "Unknown"
                    
                    if not tl.get('is_bookable'):
                         status_msg = "Full / Deadline passed"
                    else:
                         # It's technically bookable, check details via PRE
                         # Extract loginuid
                         import re
                         match = re.search(r'id="loginuid" name="loginuid" value="(\d+)"', html)
                         loginuid = match.group(1) if match else "0"
                         
                         params = {"loginuid": loginuid, "step": "PRE", "next": "", "eventid": eid, "courseid": "0"}
                         response_pre = client.ajax_request("ax.checkin.showcheckin", params)
                         
                         if "Buchungsfrist beendet" in response_pre or "Termin ist vergangen" in response_pre:
                              status_msg = "Deadline passed"
                         elif "Sie sind auf der Warteliste" in response_pre or ("Teilnahme am Termin" in response_pre and "tstornieren" in response_pre):
                              status_msg = "Already Booked/Waitlisted"
                         else:
                              status_msg = "AVAILABLE"
                              if args.book:
                                  booking_params = {
                                    "loginuid": loginuid, "step": "EVBK", "next": "", "eventid": eid, "courseid": "0",
                                    "selanicls": "S", "selanimal": "0", "note": "", "agb_ok": "on", "dat_ok": "on", "nutz_ok": "on"
                                  }
                                  response_evbk = client.ajax_request("ax.checkin.showcheckin", booking_params)
                                  if "erfolgreich" in response_evbk or "gebucht" in response_evbk:
                                      status_msg = "SUCCESSFULLY BOOKED"
                                      target_found = True
                                  else:
                                      status_msg = "Booking Failed (See log)"
                                      logger.warning(f"Booking response debug: {response_evbk[:200]}...")
                                      target_found = True
                              else:
                                  status_msg = "AVAILABLE (Dry Run)"
                                  target_found = True
                    
                    print(f"{date_str:<15} | {eid:<10} | {status_msg:<30}")
                    if target_found: break
            
            except Exception as e:
                print(f"{date_str:<15} | {'ERROR':<10} | {str(e):<30}")

    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
