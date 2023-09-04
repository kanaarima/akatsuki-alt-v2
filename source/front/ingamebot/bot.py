from api.events import send_event, channel_message_event
from api.objects import Player as AkatsukiPlayer
from osu.bancho.constants import ServerPackets
from osu.objects import Player, Channel
from osu.bancho.constants import Mods
from front.ingamebot import cmd
from api.files import DataFile
from api.logging import logger
from datetime import datetime
from api.utils import today
from config import config
from typing import Union
from osu import Game

from threading import Thread

import time

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
def on_message(sender: Player, message: str, target: Union[Player, Channel]):
    if type(target) == Channel:
        if target.name == "#announce":
            handle_announce(message)

    elif (message := message.strip()).startswith('!'):
        logger.info(f"CMD {message} ({sender})")

        # Parse command
        command, *args = message[1:].split()
        command = command.lower()

        if command in commands:
            commands[command](sender, message[1:], args)
        else:
            sender.send_message("Unknown command!")

@game.tasks.register(seconds=5)
def reload_stats():
    # Load user stats
    discord_users = DataFile(
        filepath=f"{config['common']['data_directory']}/users_statistics/users_discord.json.gz"
    )
    discord_users.load_data(default={})

    # Load players that are currently online
    linked_players = list()
    ingame_players = set()

    for user in discord_users.data.values():
        player = AkatsukiPlayer(**user[0])
        linked_players.append(player)

    # Try to load users with rx
    game.bancho.status.mods = Mods.Relax
    game.bancho.update_status()

    for player in linked_players:
        if (bancho_player := game.bancho.players.by_id(player['id'])):
            bancho_player.request_stats()
            ingame_players.add(bancho_player)

    # Try to load users with nm
    game.bancho.status.mods = Mods.NoMod
    game.bancho.update_status()

    for player in linked_players:
        if (bancho_player := game.bancho.players.by_id(player['id'])):
            bancho_player.request_stats()
            ingame_players.add(bancho_player)

    # TODO: Process player data

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
            file.data[str(userid)] = {"VN": [], "RX": [], "AP": []}
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
    try:
        retry = False

        while True:
            game.run(retry, exit_on_interrupt=True)
            game.logger.warning("Restarting...")
            retry = True
    except KeyboardInterrupt:
        exit(0)
