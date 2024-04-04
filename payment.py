""" This module contains the SeleniumPayment class for handling Selenium-based payment operations."""
import tempfile
import time
import requests
import json
from pprint import pprint
from selenium import webdriver
import selenium
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import api_constants
from selenium.webdriver.common.by import By


class SeleniumPayment:
    """
    A class for handling Selenium-based payment operations.

    Args:
        max_wait_time (int): Maximum wait time in seconds for page loading (default: 120).
        *args: Additional arguments to be passed to the Chrome options.
        **kwargs: Additional keyword arguments to be set as instance attributes.

    Attributes:
        options (Options): Chrome options for configuring the WebDriver.
        max_wait_time (int): Maximum wait time in seconds for page loading.

    Methods:
        open_html_with_selenium: Opens an HTML response using Selenium WebDriver.

    """

    def __init__(
            self,
            *args,
            max_wait_time=120,
            trip,
            empty_seat,
            seat_lck_json,
            tariff,
            **kwargs):
        """
        Initialize the Payment class.

        Args:
            *args: Variable length arguments.
            max_wait_time (int): Maximum wait time in seconds (default is 120).
            trip: Trip information.
            empty_seat: Empty seat information.
            seat_lck_json: Seat lock JSON.
            tariff: Tariff information.
            **kwargs: Variable keyword arguments.
        """
        self.options = Options()
        # self.options.add_argument("--disable-notifications")
        # self.options.add_argument("--disable-geolocation")
        # self.options.add_argument("--disable-application-cache")
        # self.options.add_argument("--disable-cache")
        # self.options.add_argument("--headless")
        self.options.add_argument("--disable-infobars")
        self.options.add_argument("--mute-audio")
        # self.options.add_argument("--disable-gpu")
        # self.options.add_argument("--no-sandbox")
        # self.options.add_argument("--disable-dev-shm-usage")
        # self.options.add_argument("--disable-extensions")
        # self.options.add_argument("--disable-software-rasterizer")
        # self.options.add_argument("--disable-setuid-sandbox")
        # self.options.add_argument("--disable-sandbox")
        # self.options.add_argument("--single-process")
        # self.options.add_argument("--ignore-certificate-errors")
        # self.options.add_argument("--ignore-ssl-errors")
        # self.options.add_argument("--disable-logging")
        # add args values to options
        for arg in args:
            self.options.add_argument(arg)

        self.max_wait_time = max_wait_time
        self.trip = trip
        self.empty_seat = empty_seat
        self.seat_lck_json = seat_lck_json
        self.tariff = api_constants.TARIFFS[tariff]
        self.vb_enroll_control_req = api_constants.vb_enroll_control_req_body.copy()
        self.is_payment_successful = None
        self.vb_enroll_control_response = None
        self.html_response = None

        # add kwargs as instance attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_price(self, trip, empty_seat):
        """
        Get the price of a trip for a given empty seat.

        Args:
            trip (dict): The trip information.
            empty_seat (dict): The information of the empty seat.

        Returns:
            float: The price of the trip for the empty seat.
        """

        req_body = api_constants.price_req_body.copy()
        req_body['yolcuList'][0]['tarifeId'] = self.tariff
        seat_info = req_body['yolcuList'][0]['seferKoltuk'][0]
        seat_info.update({
            'seferBaslikId': trip['seferId'],
            'binisTarihi': trip['binisTarih'],
            'vagonSiraNo': empty_seat['vagonSiraNo'],
            'koltukNo': empty_seat['koltukNo'],
            'binisIstasyonId': trip['binisIstasyonId'],
            'inisIstasyonId': trip['inisIstasyonId'],
            'vagonTipi': empty_seat['vagonTipId']
        })

        # send request
        response = requests.post(
            api_constants.PRICE_ENDPOINT,
            headers=api_constants.REQUEST_HEADER,
            data=json.dumps(req_body),
            timeout=10)
        response_json = json.loads(response.text)
        return int(
            response_json['anahatFiyatHesSonucDVO']['indirimliToplamUcret'])

    def process_payment(self):
        """
        Process the payment for the trip.

        This method calculates the price, updates the payment information,
        sends a request to the payment API, and handles the payment authentication process.

        Returns:
            None
        """
        price = self.get_price(self.trip, self.empty_seat)
        print(f"Price: {price}")

        self.vb_enroll_control_req['biletRezOdemeBilgileri'].update({
            'toplamBiletTutari': price,
            'krediKartiTutari': price
        })

        for seat in self.seat_lck_json['koltuklarimListesi']:
            self.vb_enroll_control_req['koltukLockList'].append(
                seat['koltukLockId'])

        response = requests.post(
            api_constants.VB_ENROLL_CONTROL_ENDPOINT,
            headers=api_constants.REQUEST_HEADER,
            data=json.dumps(self.vb_enroll_control_req),
            timeout=10)

        if response.status_code != 200:
            print("Payment failed.")
            pprint(json.loads(response.text))
            return

        response_json = json.loads(response.text)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
            temp_file.write(response.text.encode('utf-8'))
            temp_file_path = temp_file.name
            self.vb_enroll_control_response = temp_file_path

        #  Payment request
        session = requests.Session()

        acs_url = response_json['paymentAuthRequest']['acsUrl']
        pareq = response_json['paymentAuthRequest']['pareq']
        md = response_json['paymentAuthRequest']['md']
        term_url = response_json['paymentAuthRequest']['termUrl']

        form_data = {
            'PaReq': pareq,
            'MD': md,
            'TermUrl': term_url
        }

        response = session.post(acs_url, data=form_data)

        if response.status_code != 200:
            print("Payment failed.")
            pprint(json.loads(response.text))
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as temp_file:
            temp_file.write(response.text.encode('utf-8'))
            temp_file_path = temp_file.name
            self.html_response = temp_file_path

        data = [{
            "ad": "izzet can",
            "soyad": "karakuş",
            "cinsiyet": 1,
            "tarifeId": 11750067704,
            "cep": "0(534) 077-1521",
            "eposta": "izzetcankarakus@gmail.com",
            "dogumTarihi": "1994-07-14",
            "kimlikNo": "18700774442",
            "tc_degil": False
        }]

        # Convert the data to a properly formatted string
        data_str = json.dumps(data)
        data_str_js = data_str.replace('"', '\\"')

        print(f"Opening {temp_file_path} with Selenium...")
        driver = webdriver.Chrome(options=self.options)
        # Set local storage variables using execute_script

        driver.get("https://bilet.tcdd.gov.tr")
        time.sleep(5)
        driver.execute_script(
            f"window.localStorage.setItem('enrollees', \"{data_str_js}\");")
        time.sleep(5)
        driver.refresh()
        time.sleep(5)
        # To verify, you can retrieve the value like this
        value = driver.execute_script(
            "return window.localStorage.getItem('enrollees');")
        print(value)  # This should print your data

        driver.get(f"file:///{temp_file_path}")
        driver.implicitly_wait(10)
        time.sleep(5)
        driver.save_screenshot("payment_page.png")

        # Find the OTP input field and submit button
        try:
            text_input = driver.find_element(
                By.CSS_SELECTOR, "input[type='number'], input[type='text']")
            btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            if text_input and btn and btn.text:
                pprint(btn.text)
                # TODO: get this from the USER
                user_input = input("Enter the OTP: ")
                text_input.send_keys(user_input)
                btn.click()
        except selenium.common.exceptions.NoSuchElementException:
            pprint("Button element not found.")

        try:
            # Wait for the redirection from payment to the main page
            WebDriverWait(driver, self.max_wait_time).until(
                EC.url_contains("https://bilet.tcdd.gov.tr/"))
            current_url = driver.current_url
            if "odeme-sonuc" in current_url:
                self.is_payment_successful = True
                print("Payment successful.")
                # take a screenshot
                time.sleep(10)
                driver.save_screenshot("payment_success.png")
            else:
                print("Payment failed.")
                self.is_payment_successful = False
                driver.save_screenshot("payment_failed.png")
                # wait until element with some id is found
                WebDriverWait(driver, self.max_wait_time).until(
                    EC.presence_of_element_located(("id", "some_id")))

        except TimeoutException:
            print("Loading took too much time!")
