from api.events import send_event, channel_message_event
from osu.bancho.constants import ServerPackets
from osu.objects.channel import Channel
from front.ingamebot import cmd
from api.files import DataFile
from api.logging import logger
from datetime import datetime
from api.utils import today
from config import config
from osu import Game

game = Game(
    config["bot_account"]["username"],
    config["bot_account"]["password"],
    server="akatsuki.gg",
)

commands = {
    "ping": cmd.ping,
    "recommend": cmd.recommend,
    "r": cmd.recommend,
    "help": cmd.help,
    "recommend_score": cmd.recommend_score,
    "rs": cmd.recommend_score,
    "cook": cmd.recommend,
    "scoer": cmd.recommend_score,
}


@game.events.register(ServerPackets.SEND_MESSAGE)
def on_message(sender, message, target):
    if type(target) == Channel:
        if target.name == "#announce":
            handle_announce(message)
    elif message[0] == "!":  # command
        logger.info(f"CMD {message} ({sender})")
        split = message[1:].split()
        if split[0] in commands:
            commands[split[0]](sender, message[1:], split[1:])
        else:
            sender.send_message("Unknown command!")


def handle_announce(message):
    if "#1 place" in message:
        gamemode_type = message[1:3]
        userid = 0
        send_event("frontend", channel_message_event(userid, "#announce", message))
        beatmap_id = 0
        url_profile = "[https://akatsuki.gg/u/"
        url_beatmap = "[https://osu.akatsuki.gg/beatmaps/"
        for string in message.split():
            if string.startswith(url_profile):
                userid = int(string[len(url_profile) :])
            elif string.startswith(url_beatmap):
                beatmap_id = int(string[len(url_beatmap) :])
        logger.info(f"{userid} set a #1 on {beatmap_id} ({gamemode_type})")
        file = DataFile(
            f"{config['common']['data_directory']}/leaderboards/users/{today()}_1s.json.gz"
        )
        file.load_data()
        if str(userid) not in file.data:
            file.data[str(userid)] = {"VN": list(), "RX": list(), "AP": list()}
        if gamemode_type == "VN":
            file.data[str(userid)]["VN"].append(beatmap_id)
        elif gamemode_type == "RX":
            file.data[str(userid)]["RX"].append(beatmap_id)
        elif gamemode_type == "AP":
            file.data[str(userid)]["AP"].append(beatmap_id)
        file.save_data()
    else:
        logger.info(f"Can't handle announce {message}")


def main():
    retry = False

    try:
        while True:
            game.run(retry)
            game.logger.warning('Game crashed. Restarting...')
            retry = True
    except KeyboardInterrupt:
        exit(0)
