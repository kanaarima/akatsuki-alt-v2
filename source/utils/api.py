import requests
import time

class ApiHandler:

    def __init__(self, delay=1, headers={'user-agent': 'akatsukialt!/KompirBot fetch service'}):
        self.delay = delay
        self.headers = headers

    def get_request(self, URL):
        time.sleep(self.delay)
        return requests.get(URL, headers=self.headers)

