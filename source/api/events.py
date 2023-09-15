from api.files import DataFile
from api.logging import get_logger
from api.objects import Score
from typing import TypedDict
from config import config

logger = get_logger("api.events")


class ChannelMessageEvent(TypedDict):
    name: str
    userid: int
    channel: str
    message: str


class TopPlayEvent(TypedDict):
    name: str
    play_type: str
    user_id: int
    beatmap_id: int
    score: Score
    index: int
    gamemode: str


class FirstPlaceEvent(TypedDict):
    name: str
    user_id: int
    beatmap_id: int
    gamemode: str


def channel_message_event(userid, channel, message) -> ChannelMessageEvent:
    return ChannelMessageEvent(
        name="ChannelMessageEvent", userid=userid, channel=channel, message=message
    )


def top_play_event(
    user_id, beatmap_id, score, index, gamemode, play_type="pp"
) -> ChannelMessageEvent:
    return TopPlayEvent(
        name="TopPlayEvent",
        user_id=user_id,
        beatmap_id=beatmap_id,
        score=score,
        index=index,
        gamemode=gamemode,
        play_type=play_type,
    )


def first_place_event(user_id, beatmap_id, gamemode) -> FirstPlaceEvent:
    return FirstPlaceEvent(
        name="FirstPlaceEvent",
        user_id=user_id,
        beatmap_id=beatmap_id,
        gamemode=gamemode,
    )


def send_event(target, event):
    logger.info(f"sending {event['name']} event to {target}")
    file = DataFile(f"{config['common']['data_directory']}/events/{target}.json.gz")
    file.load_data(default=[])
    file.data.append(event)
    file.save_data()


def read_events(target, delete=True):
    file = DataFile(f"{config['common']['data_directory']}/events/{target}.json.gz")
    file.load_data(default=[])
    if delete:
        file.delete()
    return file.data
