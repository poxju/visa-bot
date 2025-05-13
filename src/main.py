import json
import random
import sys
import time
import threading
import platform

from datetime import datetime, timedelta
from typing import Union
import os

# Add the parent directory to the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import emoji
import requests
from loguru import logger
from prettytable import PrettyTable
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.support.ui import Select
from src.constants import COOLDOWN_TIME, EXCEPTION_TIME, RETRY_TIME, STEP_TIME
from src.utils import get_driver, load_config, my_condition
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from plyer import notification

if platform.system() == "Darwin":
    from pync import Notifier

# Configure logger to exclude timestamp
logger.remove()
logger.add(sys.stdout, format="-> {message}")

config = load_config('src/config.ini')
USERNAME = config['USVISA']['USERNAME']
PASSWORD = config['USVISA']['PASSWORD']
SCHEDULE_ID = config['USVISA']['SCHEDULE_ID']
MY_SCHEDULE_DATE = config['USVISA']['MY_SCHEDULE_DATE']
COUNTRY_CODE = config['USVISA']['COUNTRY_CODE']
LOCAL_USE = config['CHROMEDRIVER'].getboolean('LOCAL_USE')
HUB_ADDRESS = config['CHROMEDRIVER']['HUB_ADDRESS']
FACILITY_ID = sys.argv[1] if len(sys.argv) > 1 else config['USVISA']['FACILITY_ID']
NOTIFICATIONS_ENABLED = config['BOT_SETTINGS'].getboolean('notifications', fallback=False)
ALERT_EMAIL = config['BOT_SETTINGS']['alert_email']
APPOINTMENT_URL = f"https://ais.usvisa-info.com/en-tr/niv/schedule/64514601/appointment?applicants%5B%5D=76371135&applicants%5B%5D=76371301&confirmed_limit_message=1&commit=Continue"
GREEN_CIRCLE_EMOJI = emoji.emojize(':green_circle:')
RED_CIRCLE_EMJOI = emoji.emojize(':red_circle:')
MAX_DATE_COUNT = 5

if len(sys.argv) > 2:
    watch_bot = sys.argv[2].lower() == "true"
else:
    watch_bot = config['BOT_SETTINGS'].getboolean('watch_bot', fallback=False)

if len(sys.argv) > 3:
    waiting_time = int(sys.argv[3])
else:
    waiting_time = config['BOT_SETTINGS'].getint('wait_time', fallback=480)  # Default waiting time

logger.info(f"Waiting time set to {waiting_time} seconds")

driver = get_driver(local_use=LOCAL_USE, hub_address=HUB_ADDRESS, watch_bot=watch_bot)

def send_notification(title, message):
    if NOTIFICATIONS_ENABLED:
        if platform.system() == "Darwin":
            Notifier.notify(message, title=title, app_name='Visa Bot')
        else:
            notification.notify(
                title=title,
                message=message,
                app_name='Visa Bot',
                timeout=10
            )

def notify_start():
    send_notification("Visa Bot Started", "The Visa Bot process has started successfully.")

def notify_stop():
    send_notification("Visa Bot Stopped", "The Visa Bot process has been stopped.")

def notify_restart():
    send_notification("Visa Bot Restarted", "The Visa Bot process has been restarted successfully.")

def listen_for_watch_bot(driver):
    """
    Continuously checks the config file for changes in 'watch_bot'.
    If it toggles, update the browser's window position on the fly.
    """
    current_watch_bot = watch_bot
    while True:
        config = load_config('src/config.ini')
        new_watch_bot = config['BOT_SETTINGS'].getboolean('watch_bot', fallback=current_watch_bot)
        if new_watch_bot != current_watch_bot:
            current_watch_bot = new_watch_bot
            position = (0, 0) if current_watch_bot else (-10000, 0)
            try:
                driver.set_window_position(*position)
                logger.info(f"Updated browser position based on watch_bot setting: {current_watch_bot}")
            except Exception as e:
                logger.error(f"Failed to reposition the browser: {e}")
        time.sleep(1)  # Check every second

def login():
    # Open the Appointments service page for the country
    driver.get(f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv")
    time.sleep(STEP_TIME)
    while check_site_unreachable():
        logger.info("Site is unreachable. Waiting for 2 hours before retrying...")
        time.sleep(7200)  # Wait for 2 hours (7200 seconds)
        driver.refresh()
        logger.info("Page refreshed after waiting for 2 hours.")
        time.sleep(STEP_TIME)
        continue
    # Click on Continue application
    a = driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
    a.click()
    time.sleep(STEP_TIME)

    href = driver.find_element(
        By.XPATH, '//*[@id="header"]/nav/div/div/div[2]/div[1]/ul/li[3]/a')
    href.click()
    time.sleep(STEP_TIME)
    Wait(driver, 60).until(EC.presence_of_element_located((By.NAME, "commit")))

    a = driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
    a.click()
    time.sleep(STEP_TIME)

    # Fill the form
    user = driver.find_element(By.ID, 'user_email')
    user.send_keys(USERNAME)
    time.sleep(random.randint(1, 3))

    pw = driver.find_element(By.ID, 'user_password')
    pw.send_keys(PASSWORD)
    time.sleep(random.randint(1, 3))

    box = driver.find_element(By.CLASS_NAME, 'icheckbox')
    box .click()
    time.sleep(random.randint(1, 3))

    btn = driver.find_element(By.NAME, 'commit')
    btn.click()
    time.sleep(random.randint(1, 3))

    # FIXME: This is not working for now to check if login is successful
    # Wait(driver, 60).until(
    #     EC.presence_of_element_located((By.XPATH, REGEX_CONTINUE))
    # )

def is_logged_in():
    content = driver.page_source
    return content.find('error') == -1

def close_browser():
    driver.quit()
    logger.info("Browser closed.")

def restart_process():
    close_browser()
    global driver
    driver = get_driver(local_use=LOCAL_USE, hub_address=HUB_ADDRESS, watch_bot=watch_bot)
    login()
    step_by_step()

def restart_from_zero():
    """
    Restart the process from the beginning: log in and start step_by_step.
    """
    logger.info("Restarting the process from the beginning...")
    login()
    step_by_step()

def check_logged_out():
    """
    Check if the user is logged out and handle re-login if necessary.
    """
    retry_count = 0
    max_retries = 3
    while retry_count < max_retries:
        try:
            # Check for the presence of the "Important Information For Visa Applicants" header
            driver.find_element(By.XPATH, '//h1[contains(text(), "Important Information For Visa Applicants")]')
            logger.info("User is logged out. Attempting to log in again...")
            restart_from_zero()  # Restart the process from the beginning
            return
        except:
            # If the element is not found, the user is still logged in
            return
        retry_count += 1
        logger.info(f"Retrying login check... ({retry_count}/{max_retries})")
        time.sleep(5)  # Wait for 5 seconds before retrying

    logger.error("Failed to log in after multiple attempts. Exiting...")
    sys.exit(1)

def step_by_step():
    time.sleep(STEP_TIME)
    try:
        continue_button = driver.find_element(By.XPATH, '//a[@class="button primary small" and text()="Continue"]')
        continue_button.click()
        time.sleep(STEP_TIME)
        # Locate the accordion title
        accordion_title = driver.find_element(By.XPATH, '//a[@class="accordion-title" and contains(., "Reschedule Appointment")]')
        # Check if the accordion is collapsed
        if (accordion_title.get_attribute("aria-expanded") == "false"):
            accordion_title.click()
            time.sleep(STEP_TIME)
        reschedule_button = driver.find_element(By.XPATH, '//a[@class="button small primary small-only-expanded" and contains(., "Reschedule Appointment")]')
        reschedule_button.click()
        time.sleep(STEP_TIME)
        submit_button = driver.find_element(By.XPATH, '//input[@type="submit" and @value="Continue"]')
        submit_button.click()
        time.sleep(STEP_TIME)

        while True:  # Loop until available days are found
            available = available_days()  # Call available_days to check if days are available
            
            if available:  # If available days are found, break the loop
                reschedule, appointment_times = set_appointment_time()
                if reschedule:
                    logger.info("Rescheduling!")
                    send_email(
                            "Script Update",
                            "Script Status: Your script has completed successfully! Rescheduling is done! Rescheduling is done! Check the US Visa appointment page for confirmation. Good luck!",
                            "veziroglue@gmail.com",
                            appointment_times
                    )
                    send_email(
                            "Script Update",
                            "Script Status: Your script has completed successfully! Rescheduling is done! Rescheduling is done! Check the US Visa appointment page for confirmation. Good luck!",
                            ALERT_EMAIL,
                            appointment_times
                        )
                    
                    set_reschedule()
                    break
                logger.info("No available times found. Waiting for the next check...")
                continue
            
            logger.info("No available days found. Waiting for the next check...")
            next_check_time = datetime.now() + timedelta(seconds=waiting_time)
            logger.info(f"Next check at: {next_check_time.strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(waiting_time)  # Use the waiting time from the GUI
            driver.refresh()
            check_logged_out()  # Check if the user is logged out after refresh
            logger.info("Page refreshed after waiting.")
            time.sleep(STEP_TIME)
    except Exception as e:
        error_log_file = f"visa_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logger.add(error_log_file, level="ERROR", backtrace=True, diagnose=True)
        logger.error(e)
        logger.error(f"Exception occurred, retrying after {EXCEPTION_TIME} seconds...")
        time.sleep(EXCEPTION_TIME)
        restart_process()

def check_site_unreachable():
    """
    Check if the site is unreachable message is displayed.
    """
    page_source = driver.page_source
    if "This site can't be reached" in page_source:
        logger.error("This site can't be reached. Waiting for 2 hours before retrying...")
        return True
    return False

def wait_for_element(driver, by, value, timeout=300):
    """
    Wait for an element to appear on the page.
    
    :param driver: The WebDriver instance.
    :param by: The method to locate the element (e.g., By.ID, By.XPATH).
    :param value: The value to locate the element.
    :param timeout: The maximum time to wait for the element (in seconds).
    :return: The WebElement if found, otherwise None.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            element = driver.find_element(by, value)
            return element
        except:
            time.sleep(5)  # Wait for 5 seconds before trying again
    return None

def check_system():
    """
    Check if the system is busy message is displayed.
    """
    page_source = driver.page_source
    if "System is busy. Please try again later." in page_source:
        logger.error("System is busy. Trying in 5 min.")
        return True
    return False

def available_days():
    logger.info("Getting available days...")
    
    # Open the calendar by clicking the input field
    while True:
        try:
            date_input = wait_for_element(driver, By.ID, "appointments_consulate_appointment_date", timeout=300)
            if date_input:
                date_input.click()
                break
            else:
                logger.error(f"Failed to click the date input. Checking login status")
                check_logged_out()  # Check if the user is logged out after refresh

        except Exception as e:
            logger.error(f"Failed to click the date input. Checking login status")
            check_logged_out()  # Check if the user is logged out after refresh


    time.sleep(STEP_TIME)
    
    # Wait until the date picker is visible
    Wait(driver, 15).until(
        EC.visibility_of_element_located((By.ID, "ui-datepicker-div"))
    )
    
    # Get the current month and year displayed in the calendar
    current_month_year = get_current_month_year()
    logger.info(f"Starting from: {current_month_year}")
        
    # Navigate through months until the target date is reached
    target_date = datetime.strptime(MY_SCHEDULE_DATE, "%Y-%m-%d")
    current_month_year = datetime.strptime(current_month_year, "%B %Y")
    
    # Loop through months until we reach or pass the target date
    while current_month_year <= target_date:
        # Get available days for the current month
        month = current_month_year.month
        year = current_month_year.year
        
        earliest_day = get_earliest_day(year, month)
        
        if earliest_day:
            logger.info(f"Available day found: {earliest_day} {month + 1} {year}")
            select_date_from_datepicker(earliest_day, month, year)
            return True
        else:
            logger.info(f"No available days found for {current_month_year.strftime('%B %Y')}")
        
        # Check if the next month is beyond the target date
        next_month_year = current_month_year + timedelta(days=31)
        if next_month_year > target_date:
            logger.info(f"Reached the target date month: {target_date.strftime('%B %Y')}. Stopping further checks.")
            break
        
        # Press the "Next" button to navigate to the next month
        next_button = driver.find_element(By.CLASS_NAME, "ui-icon-circle-triangle-e")
        next_button.click()
        
        # Wait for the calendar to load the next month
        Wait(driver, 15).until(
            EC.visibility_of_element_located((By.ID, "ui-datepicker-div"))
        )
        
        # Update the current month and year after navigating
        current_month_year = get_current_month_year()
        current_month_year = datetime.strptime(current_month_year, "%B %Y")
    
    return False

def get_current_month_year():
    current_month_year = driver.find_element(By.CLASS_NAME, "ui-datepicker-title")
    return current_month_year.text

def get_earliest_day(year, month):
    """
    Get the earliest available day for the given month and year.
    """
    day_links = driver.find_elements(By.CSS_SELECTOR, "#ui-datepicker-div a.ui-state-default") 
    
    for link in day_links:
        # Ensure the link does not have the "ui-state-disabled" class
        if "ui-state-disabled" not in link.get_attribute("class"):
            # Return the first available day number logger.info(f"Available day found: {link.text} {month} {year}")
            return link.text
    
    return None

def select_date_from_datepicker(target_day, target_month, target_year):
    """
    Selects a specific date from the datepicker.
    
    :param target_day: Day to select (integer or string).
    :param target_month: Month to select (0-indexed, January = 0).
    :param target_year: Year to select.
    """
    logger.info(f"Trying to select the date: {target_day}-{target_month+1}-{target_year}")

    try:
        # Wait for the datepicker to be visible
        Wait(driver, 15).until(
            EC.visibility_of_element_located((By.ID, "ui-datepicker-div"))
        )

        # Navigate to the correct month and year
        while True:
            title_element = driver.find_element(By.CLASS_NAME, "ui-datepicker-title")
            current_month_year = title_element.text

            current_month, current_year = current_month_year.split()
            current_month_index = time.strptime(current_month, "%B").tm_mon - 1
            current_year = int(current_year)

            if current_year == target_year and current_month_index == target_month:
                break

            if current_year < target_year or (current_year == target_year and current_month_index < target_month):
                next_button = driver.find_element(By.CSS_SELECTOR, ".ui-datepicker-next")
                next_button.click()
            else:
                prev_button = driver.find_element(By.CSS_SELECTOR, ".ui-datepicker-prev")
                prev_button.click()

            time.sleep(1)

        # Locate all matching day elements
        day_elements = driver.find_elements(
            By.CSS_SELECTOR, f'td[data-handler="selectDay"][data-month="{target_month}"][data-year="{target_year}"] a.ui-state-default'
        )

        # Select the target day
        for day_element in day_elements:
            if day_element.text == str(target_day):
                day_element.click()
                logger.info(f"Successfully selected the date: {target_day}-{target_month + 1}-{target_year}")
                return

        logger.error("The target date was not found.")
    except Exception as e:
        logger.error(f"Failed to select the date. Error: {e}")

def set_appointment_time():
    """
    Get the earliest available time for the selected day.
    """
    time.sleep(STEP_TIME)
    # Locate the <select> element
    time_select = driver.find_element(By.ID, "appointments_consulate_appointment_time")
    
    # Initialize the Select class to interact with the <select> element
    select = Select(time_select)
    
    # Check the available options
    options = select.options
    available_times = [option.text for option in options if option.text.strip() != ""]

    if available_times:
        earliest_time = available_times[0]  # Choose the first available time
        select.select_by_visible_text(earliest_time)
        logger.info(f"Selected the appointment time: {earliest_time}")
        return True, available_times
    else:
        logger.info("No available times found.")
        return False, []

def set_reschedule():
    """
    Set the reschedule appointment.
    """
    logger.info("Setting reschedule appointment...")

def send_email(subject, body, to_email, appointment_times):
    # Mail ayarları
    smtp_server = "smtp.example.com"
    smtp_port = 587
    sender_email = "your_email@example.com"
    sender_password = "your_password"

    # Mail içeriği
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject

    # Mail gövdesi
    body += f"\n\nAvailable Appointment Times:\n{appointment_times}"
    msg.attach(MIMEText(body, "plain"))

    try:
        # SMTP sunucusuna bağlan ve mail gönder
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Şifreli bağlantı
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        logger.info("Mail başarıyla gönderildi.")
    except Exception as e:
        logger.error(f"Mail gönderimi sırasında hata oluştu: {e}")
    finally:
        server.quit()

def run_main():
    global driver
    config = load_config('src/config.ini')
    waiting_time = config['BOT_SETTINGS'].getint('wait_time', fallback=480)  # Default to 480 seconds if not set
    logger.info(f"Starting Visa Bot with waiting time: {waiting_time} seconds")
    driver = get_driver(local_use=LOCAL_USE, hub_address=HUB_ADDRESS, watch_bot=watch_bot)
    # Start the listener thread
    watcher_thread = threading.Thread(target=listen_for_watch_bot, args=(driver,), daemon=True)
    watcher_thread.start()

    login()

    RETRY_COUNT = 0
    MAX_RETRY = 3

    notify_start()

    while True:
        if RETRY_COUNT > MAX_RETRY:
            logger.error("Maximum retry limit reached. Exiting...")
            break

        try:
            if step_by_step():
                break
        except Exception as e:
            RETRY_COUNT += 1
            error_log_file = f"visa_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            logger.add(error_log_file, level="DEBUG", backtrace=True, diagnose=True)
            logger.error(e)
            logger.error(f"Exception occurred, retrying after {EXCEPTION_TIME} seconds... (Retry {RETRY_COUNT}/{MAX_RETRY})")
            time.sleep(EXCEPTION_TIME)
            restart_process()

def stop_main():
    close_browser()
    notify_stop()

def restart_main():
    restart_process()
    notify_restart()

if __name__ == "__main__":
    run_main()

