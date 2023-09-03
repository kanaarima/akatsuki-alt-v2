from api.files import DataFile
from typing import TypedDict
from config import config


class ChannelMessageEvent(TypedDict):
    name: str
    userid: int
    channel: str
    message: str


class RenderEvent(TypedDict):
    name: str
    userid: int
    render_link: str


def channel_message_event(userid, channel, message) -> ChannelMessageEvent:
    return ChannelMessageEvent(
        name="ChannelMessageEvent", userid=userid, channel=channel, message=message
    )


def render_event(userid, render_link) -> ChannelMessageEvent:
    return RenderEvent(name="RenderEvent", userid=userid, render_link=render_link)


def send_event(target, event):
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
