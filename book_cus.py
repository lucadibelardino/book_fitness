import os
import time
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

def main():
    print("=== CUS Torino Free Fitness Auto-Booking ===")
    
    # Load .env file if it exists (for local testing)
    load_dotenv()
    
    username = os.environ.get("CUSTORINO_USERNAME")
    password = os.environ.get("CUSTORINO_PASSWORD")
    
    if not username or not password:
        print("[!] Credentials not found in environment variables. Please set CUSTORINO_USERNAME and CUSTORINO_PASSWORD.")
        return

    # Use Rome timezone to ensure correct date calculation
    rome_tz = pytz.timezone('Europe/Rome')
    current_time = datetime.now(rome_tz)
    
    # Check if we're running in GitHub Actions to determine headless mode
    is_ci = os.environ.get("CI") == "true"
    
    # If in CI, we want to ensure we run strictly after midnight (00:00:01) to book exactly when slots open
    if is_ci:
        # If we started before midnight (e.g. 23:50), wait until 00:00:01 of the next day
        if current_time.hour == 23:
            midnight = current_time.replace(hour=0, minute=0, second=1, microsecond=0) + timedelta(days=1)
            wait_seconds = (midnight - current_time).total_seconds()
            if wait_seconds > 0:
                print(f"[*] CI Mode: Started early. Waiting {wait_seconds:.2f} seconds until {midnight.strftime('%H:%M:%S')}...")
                time.sleep(wait_seconds)
    
    # Recalculate target date after potential sleep
    now = datetime.now(rome_tz)
    tomorrow = now + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%d/%m/%Y")
    print(f"[*] Target date: {tomorrow_str} (time: 18:30 - 20:00)")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=is_ci, slow_mo=500 if not is_ci else 0)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        print("[*] Navigating to Login page...")
        page.goto("https://servizi.custorino.it/LoginAreaRiservata.aspx")
        
        try:
            print("[*] Filling login form...")
            page.locator("input[type='text']").first.fill(username)
            page.locator("input[type='password']").fill(password)
            page.locator("input[type='submit'], button[type='submit'], a.btn").first.click()
            
            print("[*] Waiting for post-login page load...")
            page.wait_for_load_state("networkidle")
            time.sleep(2)
        except Exception as e:
            print(f"[!] Error during login: {e}")
            
        print("[*] Navigating to Free Fitness page...")
        page.goto("https://servizi.custorino.it/FreeFitness.aspx")
        page.wait_for_load_state("networkidle")
        
        print(f"[*] Selecting day: {tomorrow.day}")
        try:
            # Clicca sul giorno del mese nel calendario
            page.get_by_role("link", name=str(tomorrow.day), exact=True).click()
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            print("[*] Selecting time slot: 18.30-20")
            row = page.locator('tr:has-text("18.30-20")')
            
            # Controlla se contiene la parola 'Full'
            text_content = row.inner_text()
            if "Full" in text_content:
                print(f"[!] The slot '18.30-20' is Full on {tomorrow_str}.")
            else:
                row.get_by_role('checkbox').check()
                
                if is_ci:
                    print("[*] [CI] Confirming booking...")
                    page.locator('#UC_FreeFitness_LBConferma').click()
                    page.wait_for_load_state("networkidle")
                    print("[*] Booking confirmed successfully!")
                else:
                    print("\n" + "="*50)
                    print("[*] DRY RUN. Slot '18.30-20' selected!")
                    print("[*] Skipping final confirmation click. Inspect if needed.")
                    print("="*50 + "\n")
                    page.pause()
                    
        except Exception as e:
            print(f"[!] Error during booking selection: {e}")
        
        browser.close()
        print("[*] Script finished.")

if __name__ == "__main__":
    main()
