import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from client import ReitbuchClient
from parser import parse_available_lessons
import re
from datetime import date, datetime, timedelta

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Config
TOKEN = os.environ.get("TELEGRAM_TOKEN")
USER = os.environ.get("REITBUCH_USER")
PWD = os.environ.get("REITBUCH_PASSWORD")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def check_lessons(do_booking=False):
    client = ReitbuchClient()
    if not client.login(USER, PWD):
        return ["⚠️ Login failed!"]

    today = date.today()
    days_ahead = 5 - today.weekday()
    if days_ahead <= 0: days_ahead += 7
    next_saturday = today + timedelta(days=days_ahead)
    potential_dates = [next_saturday + timedelta(weeks=i) for i in range(6)]
    target_dates = [d for d in potential_dates if (d - today).days > 14]
    
    results = []
    
    for target_date in target_dates:
        date_str = target_date.strftime("%d.%m.%Y")
        start_of_current_week = today - timedelta(days=today.weekday())
        start_of_target_week = target_date - timedelta(days=target_date.weekday())
        week_diff = (start_of_target_week - start_of_current_week).days // 7
        
        try:
            html = client.get_weekly_plan(week_diff)
            lessons = parse_available_lessons(html)
            target_lessons = [l for l in lessons if "Dressur Standard" in l['title'] and "09:00" in l['time']]
            
            if not target_lessons:
                results.append(f"📅 {date_str}: Not found")
                continue

            for tl in target_lessons:
                eid = tl['id']
                status_msg = "Unknown"
                
                match = re.search(r'id="loginuid" name="loginuid" value="(\d+)"', html)
                loginuid = match.group(1) if match else "0"
                
                params = {"loginuid": loginuid, "step": "PRE", "next": "", "eventid": eid, "courseid": "0"}
                response_pre = client.ajax_request("ax.checkin.showcheckin", params)
                
                if "Buchungsfrist beendet" in response_pre or "Termin ist vergangen" in response_pre:
                    status_msg = "Deadline passed"
                elif "Sie sind auf der Warteliste" in response_pre:
                    status_msg = "Waitlisted"
                elif "bereits gebucht" in response_pre: # Guessing text
                    status_msg = "Already Booked"
                elif "alle Teilnehmerplätze belegt" in response_pre:
                    status_msg = "Full (No Waitlist)"
                else:
                    all_actions = re.findall(r"ShowCheckin\s*\(\s*['\"]EVBK['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", response_pre)
                    if any("STORN" in a for a in all_actions):
                        status_msg = "Already Booked (Can Cancel)"
                    elif "BOOK_T" in all_actions:
                        status_msg = "AVAILABLE (Booking)"
                        if do_booking:
                            # Booking Logic
                            b_params = {
                                "loginuid": loginuid, "step": "EVBK", "next": "BOOK_T", "eventid": eid, "courseid": "0",
                                "selanicls": "S", "selanimal": "S:0", "note": "", "selpayopt": "BILL"
                            }
                            resp = client.ajax_request("ax.checkin.showcheckin", b_params)
                            if "erfolgreich" in resp or "gebucht" in resp:
                                status_msg = "Booking SUCCESSFUL! 🎉"
                            else:
                                status_msg = "Booking FAILED ❌"
                    elif "BOOK_W" in all_actions:
                        status_msg = "AVAILABLE (Waitlist)"
                        if do_booking:
                            b_params = {
                                "loginuid": loginuid, "step": "EVBK", "next": "BOOK_W", "eventid": eid, "courseid": "0",
                                "selanicls": "S", "selanimal": "S:0", "note": "", "selpayopt": "BILL"
                            }
                            resp = client.ajax_request("ax.checkin.showcheckin", b_params)
                            if "erfolgreich" in resp:
                                status_msg = "Waitlisting SUCCESSFUL! 📝"
                            else:
                                status_msg = "Waitlisting FAILED ❌"
                
                results.append(f"📅 {date_str}: {status_msg}")
                
        except Exception as e:
            results.append(f"📅 {date_str}: ERROR {e}")
            
    return results

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Checking Reitbuch... moment!")
    lines = check_lessons(do_booking=False)
    msg = "🐴 Reitbuch Status:\n" + "\n".join(lines)
    await update.message.reply_text(msg)

async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    lines = check_lessons(do_booking=True)
    msg = "🐴 Daily Booking Report:\n" + "\n".join(lines)
    if CHAT_ID:
        await context.bot.send_message(chat_id=CHAT_ID, text=msg)

def main():
    if not TOKEN:
        logger.error("No Token")
        sys.exit(1)
        
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("status", status))
    
    # Schedule Job at 00:01
    # Note: timezone might be UTC if not specified
    app.job_queue.run_daily(daily_job, time=datetime.strptime("00:01", "%H:%M").time(), days=(0,1,2,3,4,5,6))
    
    # Also run once on start? No.
    
    logger.info("Bot started")
    app.run_polling()

if __name__ == '__main__':
    main()
