from playwright.sync_api import sync_playwright
import time
from datetime import datetime
from datetime import timedelta
import threading
import re
import os

should_store_auth = False  # Set to True if you want to store auth state
lock = threading.Lock()


class CourtBookingThread(threading.Thread):
    def __init__(self, username, password, slot, court_number):
        super().__init__()
        self.username = username
        self.password = password
        self.slot = slot
        self.court_number = court_number

    def log(self, message):
        with lock:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {self.username}: {message}", flush=True)

    def run(self):
        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=False)
            self.context = self.create_context()
            self.page = self.context.new_page()
            self.page.set_default_timeout(10000)

            self.login()
            self.wait_till_booking_time()
            self.goto_booking_page()
            self.select_court()
            self.book()

            while True:
                time.sleep(1)

    def convert_to_filename(self):
        return re.sub(r"[^a-zA-Z0-9]", "_", self.username)

    def login(self):
        self.page.goto("https://bookings.better.org.uk/")
        # self.page.click("button:has-text('Accept All Cookies')")
        self.page.click("button:has-text('Reject All')")

        self.page.click("button:has-text('Log in')")

        self.page.fill("id=username", self.username)  # Replace with your username
        self.page.fill("id=password", self.password)  # Replace with your password

        self.page.click(
            "button.Button__StyledButton-sc-5h7i9w-1.ekmAlR.SharedLoginComponent__LoginButton-sc-hdtxi2-5.eHLAhM"
        )
        self.page.wait_for_selector('[data-testid="home-dashboard"]')

        self.log("Logged in successfully.")
        if should_store_auth:
            self.context.storage_state(path=f"auth/{self.convert_to_filename()}.json")

    def goto_booking_page(self):
        now = datetime.now()
        self.log(f"Current date and time: {now.day}/{now.month}/{now.year} {now.hour}:{now.minute}")
        booking_date = now + timedelta(days=7)
        day = booking_date.day
        month = booking_date.month
        year = booking_date.year
        booking_date = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
        booking_url = f"https://bookings.better.org.uk/location/hillingdon-sports-leisure-centre/badminton-40min/{booking_date}/by-time/slot/{self.slot}"
        self.log(f"Booking URL: {booking_url}")

        while True:
            self.page.goto(booking_url)
            self.page.wait_for_selector(".ContentHeader__Title-sc-kle3tz-1.btzmJO")
            if self.page.url == booking_url:
                break
            self.log("retrying to navigate to booking self.page...")

        self.log("Navigated to booking page successfully.")

    def wait_till_booking_time(self):
        booking_time = datetime.now().replace(hour=22, minute=0, second=0)

        while True:
            if datetime.now() >= booking_time:
                break

    def select_court(self):
        self.page.click("div.css-thk6w-control")
        self.page.click(f"div[role='option']:has-text('Sports Hall Court {self.court_number}')")

    def book(self):
        self.page.click("button:has-text('Book now')")
        self.page.click("button:has-text('Confirm booking')")

    def create_context(self):
        if should_store_auth:
            auth_file = f"auth/{self.convert_to_filename(self.username)}.json"
            if os.path.isfile(auth_file):
                self.log(f"Using existing auth file: {auth_file}")
                context = self.browser.new_context(storage_state=auth_file)
            else:
                self.log(f"No auth file found for {self.username}. Creating a new one.")
                context = self.browser.new_context()
        else:
            context = self.browser.new_context()
        return context

    def attach_network_call_interceptor(self):
        self.page.on("request", lambda r: self.log(f"{r.method} {r.url}\nHeaders: {r.headers}\nData: {r.post_data}"))
        self.page.on("response", lambda response: self.log(f"⬅️ {response.status} {response.url}"))


court_bookings = {
    CourtBookingThread("badders2024@gmail.com", "Badders123$", "17:20-18:00", 1),
    CourtBookingThread("deepan.shah@thermofisher.com", "Badminton_2024", "17:20-18:00", 2),
    CourtBookingThread("manish.arora@iqvia.com", "Manish@13", "17:20-18:00", 3),
}

for court_booking in court_bookings:
    threading.Thread(target=court_booking.run).start()
