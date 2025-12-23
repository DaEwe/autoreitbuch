import os
import sys
import logging
from client import ReitbuchClient
from parser import parse_available_lessons

logging.basicConfig(
    level=logging.WARNING, 
    format='%(message)s'   
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("parser").setLevel(logging.WARNING)

def main():
    username = os.environ.get("REITBUCH_USER")
    password = os.environ.get("REITBUCH_PASSWORD")

    if not username or not password:
        logger.error("Error: REITBUCH_USER and REITBUCH_PASSWORD environment variables must be set.")
        sys.exit(1)

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
        
        from datetime import date, datetime, timedelta
        today = date.today()
        
        target_dates = []
        if args.date:
            try:
                dt = datetime.strptime(args.date, "%d.%m.%Y").date()
                target_dates = [dt]
            except ValueError:
                logger.error("Invalid date format. Please use DD.MM.YYYY")
                sys.exit(1)
        else:
            days_ahead = 5 - today.weekday()
            if days_ahead <= 0: days_ahead += 7
            next_saturday = today + timedelta(days=days_ahead)
            
            # Check next 6 weeks to catch lessons > 14 days away
            potential_dates = [next_saturday + timedelta(weeks=i) for i in range(6)]
            # Filter: must be more than 14 days in the future
            target_dates = [d for d in potential_dates if (d - today).days > 14]
        
        target_found = False
        
        for target_date in target_dates:
            date_str = target_date.strftime("%d.%m.%Y")
            
            # Calculate week offset
            # Reitbuch likely counts week diffs.
            # Get Monday of current week
            start_of_current_week = today - timedelta(days=today.weekday())
            # Get Monday of target week
            start_of_target_week = target_date - timedelta(days=target_date.weekday())
            
            week_diff = (start_of_target_week - start_of_current_week).days // 7
            
            try:
                html = client.get_weekly_plan(week_diff)
                lessons = parse_available_lessons(html)
                
                target_lessons = [l for l in lessons if "Dressur Standard" in l['title'] and "09:00" in l['time']]
                
                if not target_lessons:
                    print(f"{date_str:<15} | {'-':<10} | {'Not found':<30}")
                    continue

                for tl in target_lessons:
                    eid = tl['id']
                    status_msg = "Unknown"
                    
                    # Expected context format: 'col_YYYY-MM-DD' or just 'YYYY-MM-DD' depending on parser
                    target_iso = target_date.strftime("%Y-%m-%d")
                    lesson_date_ctx = tl.get('date_context', '')
                    
                    if target_iso not in lesson_date_ctx:
                         status_msg = f"Date Mismatch ({lesson_date_ctx})"
                         print(f"{date_str:<15} | {eid:<10} | {status_msg:<30}")
                         continue
                    
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
                         elif "Sie sind auf der Warteliste" in response_pre or ("Teilnahme am Termin" in response_pre and "stornieren" in response_pre):
                              status_msg = "Already Booked/Waitlisted"
                         else:
                              # Start with default assumption
                              is_waitlist = "Warteliste" in response_pre
                              
                              if is_waitlist:
                                  next_param = "BOOK_W"
                                  action_desc = "Waitlisting"
                              else:
                                  next_param = "BOOK_T"
                                  action_desc = "Booking"

                              status_msg = f"AVAILABLE ({action_desc})"
                              
                              if args.book:
                                  booking_params = {
                                    "loginuid": loginuid, "step": "EVBK", "next": next_param, "eventid": eid, "courseid": "0",
                                    "selanicls": "S", "selanimal": "S:0", "note": "", "selpayopt": "BILL"
                                  }
                                  response_evbk = client.ajax_request("ax.checkin.showcheckin", booking_params)
                                  if "erfolgreich" in response_evbk or "gebucht" in response_evbk or "Sie sind Teilnehmer" in response_evbk:
                                      status_msg = f"{action_desc} SUCCESSFUL"
                                      target_found = True
                                  else:
                                      status_msg = f"{action_desc} FAILED (See log)"
                                      logger.warning(f"Booking response debug: {response_evbk[:200]}...")
                                      target_found = True
                              else:
                                  status_msg = f"AVAILABLE ({action_desc}) - Dry Run"
                                  target_found = True
                    
                    print(f"{date_str:<15} | {eid:<10} | {status_msg:<30}")
                    # Continue searching other dates even if found
            
            except Exception as e:
                print(f"{date_str:<15} | {'ERROR':<10} | {str(e):<30}")

    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
