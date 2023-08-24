from utils.api import ApiHandler
from typing import TypedDict
from config import config
import time


class RenderConfig(TypedDict):
    resolution: str
    global_volume: int
    music_volume: int
    hitsound_volume: int
    showSliderBreaks: bool
    skin: str


requests = ApiHandler(delay=10, base_url="https://apis.issou.best/ordr/")
default = RenderConfig(
    resolution="1280x720",
    globalVolume=100,
    musicVolume=90,
    hitsoundVolume=100,
    showSliderBreaks=True,
    skin="WhiteCat (CK 1.0)",
)


def send_render(replayURL, username, config=default):
    payload = config.copy()
    payload["replayURL"] = replayURL
    payload["username"] = username
    payload["verificationKey"] = "devmode_success"
    req = requests.post_request("renders", data=payload)
    if req.status_code != 201:
        print(req.status_code)
        print(req.content)
        return None
    data = req.json()
    finalreq = requests.get_request("renders", data={"renderID": data["renderID"]})
    if req.status_code != 200:
        print(req.status_code)
        print(req.content)
        return None
    time.sleep(5)
    for render in finalreq.json()["renders"]:
        if render["renderID"] == data["renderID"]:
            return render["videoUrl"]
    return None
