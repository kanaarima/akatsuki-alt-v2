import requests
import time

class ApiHandler:

    def __init__(self, delay=1):
        self.delay = delay

    def get_request(self, URL):
        time.sleep(self.delay)
        return requests.get(URL)

