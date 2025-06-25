from playwright.sync_api import sync_playwright
import time
from datetime import datetime
from datetime import timedelta
import threading
import re
import pytesseract
from time import sleep
import cv2

should_store_auth = False  # Set to True if you want to store auth state
lock = threading.Lock()
parking_location_code = "808605\n"


class ParkingThread(threading.Thread):
    def __init__(self, username, password, number_plate):
        super().__init__()
        self.username = username
        self.password = password
        self.number_plate = number_plate

    def log(self, message):
        with lock:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {self.username}: {message}", flush=True)

    def run(self):
        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=False)
            self.page = self.browser.new_page()
            self.page.set_default_timeout(10000)

            self.login()
            self.park()

            while True:
                time.sleep(1)

    def convert_to_filename(self):
        return re.sub(r"[^a-zA-Z0-9]", "_", self.username)

    def login(self):
        self.page.goto("https://m2.paybyphone.co.uk/login")

        self.page.wait_for_selector("#onetrust-reject-all-handler")
        self.page.click("#onetrust-reject-all-handler")
        self.page.fill("input[name='username']", self.username)
        self.page.fill("input[name='password']", self.password)
        self.page.click("button:has-text('Sign in')")

        self.log("Logged in successfully.")

    def park(self):
        self.page.click("button:has-text('Park')")

        self.page.fill("input[name='locationNumber']", parking_location_code)
        self.page.click("div.MuiSelect-root[role='button']")
        
        sleep(5)
        flutter_element = self.page.locator("flutter-view")
        flutter_element.screenshot(path="flutter_dropdown.png")
        image = cv2.imread("flutter_dropdown.png")
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        self.log(data)
        return
      
        self.page.click("button:has-text('continue')")

        self.page.fill("input[name='duration']", "30")
        self.page.click("button:has-text('continue')")

        self.page.click("button:has-text('Not now')")

        self.page.click("button:has-text('Park')")
        # self.page.click("button:has-text('View parking session')")



ParkingThread("7737687865", "Loveyou1@", "HJ71VZP").run()

for court_booking in court_bookings:
    threading.Thread(target=court_booking.run).start()
