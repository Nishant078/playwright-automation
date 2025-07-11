from playwright.sync_api import sync_playwright
import time
from datetime import datetime
from datetime import timedelta
import threading
import re
import os
import json

should_store_auth = False  # Set to True if you want to store auth state
lock = threading.Lock()


class CourtBookingThread(threading.Thread):
    def __init__(self, username, password, time_slot, court_number):
        super().__init__()
        self.username = username
        self.password = password
        self.time_slot = time_slot
        self.court_number = court_number
        self.auth_file_path = "auth/" + re.sub(r"[^a-zA-Z0-9]", "_", self.username) + ".json"

    def log(self, message):
        with lock:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {self.username}: {message}", flush=True)

    def run(self):
        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=False)
            self.context = self.create_context()
            self.context.set_default_timeout(0)
            self.page = self.context.new_page()

            self.log("Starting...")
            self.goto_home_page()
            if not self.is_logged_in():
                self.login()
            self.wait_till_booking_time()
            self.goto_booking_page()
            self.select_court()
            self.book()
            self.done()

    def done(self):
        while True:
            time.sleep(1000)

    def goto_home_page(self):
        self.page.goto("https://bookings.better.org.uk/")
        if not should_store_auth:
            self.page.click("button:has-text('Reject All')")
        self.log("Home page loaded.")

    def is_logged_in(self):
        if not should_store_auth:
            return False
        self.page.wait_for_selector('[data-testid="home-dashboard"]')
        if self.page.query_selector("button:has-text('Log in')"):
            self.log("Not logged in.")
            return False
        self.log("Already logged in.")
        return True

    def login(self):
        self.log("Logging in...")

        self.page.click("button:has-text('Log in')")

        self.page.fill("id=username", self.username)  # Replace with your username
        self.page.fill("id=password", self.password)  # Replace with your password

        self.page.click(
            "button.Button__StyledButton-sc-5h7i9w-1.ekmAlR.SharedLoginComponent__LoginButton-sc-hdtxi2-5.eHLAhM"
        )
        self.page.wait_for_selector('[data-testid="home-dashboard"]')

        self.log("Logged in successfully.")
        if should_store_auth:
            self.log("Storing auth state...")
            self.context.storage_state(path=self.auth_file_path)

    def wait_till_booking_time(self):
        self.log("Waiting for booking time...")
        booking_time = datetime.now().replace(hour=22, minute=0, second=0, microsecond=300000)
        while datetime.now() < booking_time:
            pass
        self.log(f"Proceeding to book : {datetime.now()}")

    def goto_booking_page(self):
        now = datetime.now()
        booking_date = now + timedelta(days=7)
        day = booking_date.day
        month = booking_date.month
        year = booking_date.year
        booking_date = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
        booking_url = f"https://bookings.better.org.uk/location/hillingdon-sports-leisure-centre/badminton-40min/{booking_date}/by-time/slot/{self.time_slot}"
        self.log(f"Booking URL: {booking_url}")

        while True:
            self.page.goto(booking_url)
            self.page.wait_for_selector(".ContentHeader__Title-sc-kle3tz-1.btzmJO")
            if self.page.url == booking_url:
                break
            self.log("retrying to navigate to booking self.page...")

        self.log("Navigated to booking page successfully.")

    def select_court(self):
        self.page.click("div.css-thk6w-control")
        self.page.click(f"div[role='option']:has-text('Sports Hall Court {self.court_number}')")

    def book(self):
        self.page.click("button:has-text('Book now')")
        self.page.click("button:has-text('Confirm booking')")

    def create_context(self):
        if should_store_auth:
            if os.path.isfile(self.auth_file_path):
                self.log(f"Using existing auth file: {self.auth_file_path}")
                context = self.browser.new_context(storage_state=self.auth_file_path)
            else:
                self.log(f"No auth file found for {self.username}. Creating a new auth context.")
                context = self.browser.new_context()
        else:
            context = self.browser.new_context()
        return context

    def attach_network_call_interceptor(self):
        self.page.on("request", lambda r: self.log(f"{r.method} {r.url}\nHeaders: {r.headers}\nData: {r.post_data}"))
        self.page.on("response", lambda response: self.log(f"⬅️ {response.status} {response.url}"))


court_bookings = [
    # CourtBookingThread("badders2024@gmail.com", "Badders123$", "20:40-21:20", 1),
    # CourtBookingThread("deepan.shah@thermofisher.com", "Badminton_2024", "21:20-22:00", 1),
    # CourtBookingThread("manish.arora@iqvia.com", "Manish@13", "17:20-18:00", 3),
    # CourtBookingThread("cooldave001@yahoo.co.uk", "Health@23-AD", "17:20-18:00", 3),
]

# read BookingInstruction.json for booking instructions
with open("BookingInstruction.json", "r") as f:
    booking_instructions = json.load(f)["booking_instructions"]
    for booking_instruction in booking_instructions:
        if booking_instruction["should_book"]:
            print(
                f"Will be booking for {booking_instruction['username']} \n\t- at {booking_instruction['time_slot']} on court {booking_instruction['court_number']}"
            )
            court_bookings.append(
                CourtBookingThread(
                    booking_instruction["username"],
                    booking_instruction["password"],
                    booking_instruction["time_slot"],
                    booking_instruction["court_number"],
                )
            )

threads = []
for court_booking in court_bookings:
    thread = threading.Thread(target=court_booking.run)
    thread.start()
    threads.append(thread)

for thread in threads:
    thread.join()
