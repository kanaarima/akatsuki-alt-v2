from datetime import datetime, timedelta
import requests
import time

DEFAULT_HEADERS = {"user-agent": "akatsukialt!/KompirBot fetch service"}


class ApiHandler:
    def __init__(self, delay=1, base_url="", headers=DEFAULT_HEADERS):
        self.delay = delay
        self.base_url = base_url
        self.headers = headers
        self.lock = False
        self.last = datetime.now()

    def get_request(self, URL, data=None):
        self._wait()
        self._lock()
        req = requests.get(f"{self.base_url}{URL}", headers=self.headers, data=data)
        self.lock = False
        return req

    def post_request(self, URL, data=None):
        self._wait()
        self._lock()
        req = requests.post(f"{self.base_url}{URL}", headers=self.headers, data=data)
        self.lock = False
        return req

    def _wait(self):
        while self.lock:
            time.sleep(0.1)
        elapsed = (datetime.now() - self.last).total_seconds()
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def _lock(self):
        self.lock = True
        self.last = datetime.now()
