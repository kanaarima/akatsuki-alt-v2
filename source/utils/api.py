import requests
import time

class ApiHandler:

    def __init__(self, delay=1, base_url="", headers={'user-agent': 'akatsukialt!/KompirBot fetch service'}):
        self.delay = delay
        self.base_url = base_url
        self.headers = headers

    def get_request(self, URL):
        time.sleep(self.delay)
        return requests.get(f"{self.base_url}{URL}", headers=self.headers)

