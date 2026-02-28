import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from client import ReitbuchClient
from parser import parse_available_lessons, parse_my_events
import re
from datetime import date, datetime, timedelta, time
import pytz
import time as time_module
import sys

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
                            b_params = {
                                "loginuid": loginuid, "step": "EVBK", "next": "BOOK_T", "eventid": eid, "courseid": "0",
                                "selanicls": "S", "selanimal": "S:0", "note": "", "selpayopt": "BILL"
                            }
                            client.ajax_request("ax.checkin.showcheckin", b_params)
                            # Verify via erneuten PRE-Call — STORN = Buchung erfolgreich
                            verify = client.ajax_request("ax.checkin.showcheckin", params)
                            verify_actions = re.findall(r"ShowCheckin\s*\(\s*['\"]EVBK['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", verify)
                            if any("STORN" in a for a in verify_actions) or "Sie sind Teilnehmer" in verify or "gebucht" in verify:
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
                            client.ajax_request("ax.checkin.showcheckin", b_params)
                            # Verify via erneuten PRE-Call — STORN = auf Warteliste
                            verify = client.ajax_request("ax.checkin.showcheckin", params)
                            verify_actions = re.findall(r"ShowCheckin\s*\(\s*['\"]EVBK['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", verify)
                            if any("STORN" in a for a in verify_actions) or "Warteliste" in verify or "erfolgreich" in verify:
                                status_msg = "Waitlisting SUCCESSFUL! 📝"
                            else:
                                status_msg = "Waitlisting FAILED ❌"
                
                results.append(f"📅 {date_str}: {status_msg}")
                
        except Exception as e:
            results.append(f"📅 {date_str}: ERROR {e}")
            
    return results

def check_account_status():
    client = ReitbuchClient()
    if not client.login(USER, PWD):
        return ["⚠️ Login fehlgeschlagen"]

    try:
        resp = client.client.get("/myaccount.events.php")
        events = parse_my_events(resp.text)
        if not events:
            return ["(Keine zukünftigen Termine gefunden)"]

        STATUS_ICON = {'gebucht': '✅', 'warteliste': '🕐', 'unbekannt': '❓'}
        lines = []
        for e in events:
            icon = STATUS_ICON.get(e['status'], '❓')
            status_label = {'gebucht': 'Gebucht', 'warteliste': 'Warteliste', 'unbekannt': '?'}.get(e['status'], '?')
            lines.append(f"{icon} {e['date_str']} — {e['title']} ({e['teacher']}) [{status_label}]")
        return lines
    except Exception as ex:
        return [f"Fehler: {ex}"]

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Lade Buchungen...")

    lines = check_account_status()
    msg = "🐴 Meine Buchungen:\n\n" + "\n".join(lines)
    await update.message.reply_text(msg)


async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    # Sniper Mode: Run for 6 minutes (start 23:59 -> end 00:05)
    start_ts = time_module.time()
    duration = 6 * 60 
    
    status_message = None
    if CHAT_ID:
        status_message = await context.bot.send_message(chat_id=CHAT_ID, text="🚁 Sniper-Modus gestartet! (Scanne alle 5s...)")

    last_lines = []
    attempt = 0
    
    while time_module.time() - start_ts < duration:
        attempt += 1
        lines = check_lessons(do_booking=True)
        last_lines = lines
        
        # Check for success
        if any("SUCCESSFUL" in line for line in lines):
            msg = "🐴 🎯 VOLLETREFFER! (Sniper Success):\n\n"
            msg += "📅 **Kommende Termine (Wochenplan):**\n" + "\n".join(lines)
            if CHAT_ID:
                await context.bot.send_message(chat_id=CHAT_ID, text=msg)
            return # Stop spamming
            
        # Update Status Message (every 20s or every change? To avoid rate limit)
        # Let's update every 4th attempt (20s)
        if status_message and attempt % 4 == 0:
            try:
                current_status = "\n".join(lines)
                await context.bot.edit_message_text(
                    chat_id=CHAT_ID, 
                    message_id=status_message.message_id, 
                    text=f"🚁 Sniper läuft... (Versuch {attempt})\n\n{current_status}"
                )
            except Exception as e:
                pass # Ignore "message not modified" errors

        # Wait 5s
        time_module.sleep(5)
        
    # Final report if nothing worked
    lines_account = check_account_status()
    msg = "🐴 Sniper beendet (Kein Erfolg):\n\n"
    msg += "📅 **Letzter Status:**\n" + "\n".join(last_lines) + "\n\n"
    msg += "📒 **Buchungshistorie (Konto):**\n" + "\n".join(lines_account)
    
    if CHAT_ID:
        await context.bot.send_message(chat_id=CHAT_ID, text=msg)

def main():
    if not TOKEN:
        logger.error("No Token")
        sys.exit(1)
        
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("status", status))
    
    # Schedule Job at 23:59 Europe/Berlin
    berlin_tz = pytz.timezone('Europe/Berlin')
    target_time = time(23, 59, tzinfo=berlin_tz)
    app.job_queue.run_daily(daily_job, time=target_time, days=(0,))  # 0 = Sonntag
    
    # Also run once on start? No.
    
    logger.info("Bot started")
    app.run_polling()

if __name__ == '__main__':
    main()
