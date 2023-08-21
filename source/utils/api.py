import requests
import time

DEFAULT_HEADERS = {"user-agent": "akatsukialt!/KompirBot fetch service"}


class ApiHandler:
    def __init__(self, delay=1, base_url="", headers=DEFAULT_HEADERS):
        self.delay = delay
        self.base_url = base_url
        self.headers = headers

    def get_request(self, URL):
        time.sleep(self.delay)
        return requests.get(f"{self.base_url}{URL}", headers=self.headers)
