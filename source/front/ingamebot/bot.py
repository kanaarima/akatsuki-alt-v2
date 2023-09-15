from api.objects import gamemodes, Player as AkatsukiPlayer
from api.events import send_event, first_place_event
from api.beatmaps import load_beatmap
from api.logging import get_logger
from api.database import conn
from api.utils import today

from osu.bancho.constants import ServerPackets
from osu.objects import Player, Channel
from osu.bancho.constants import Mods

from front.ingamebot import commands

from config import config
from typing import Union
from osu import Game
from time import sleep

game = Game(
    config["bot_account"]["username"],
    config["bot_account"]["password"],
    server="akatsuki.gg",
)

logger = get_logger("osu.bot")


@game.events.register(ServerPackets.SEND_MESSAGE)
def on_message(sender: Player, message: str, target: Union[Player, Channel]):
    if type(target) == Channel:
        if target.name == "#announce":
            handle_announce(message)

    elif (message := message.strip()).startswith("!"):
        # Command was executed
        logger.info(f"{sender} executed a command: {message}")

        # Parse command
        trigger, *args = message[1:].split()
        trigger = trigger.lower()

        for command in commands.commands:
            if trigger in command.triggers:
                command.function(sender, message[1:], args)
                return

        sender.send_message("Unknown command!")


@game.events.register(ServerPackets.USER_STATS)
def stats_update(player: Player):
    # TODO: Process player data
    pass


@game.tasks.register(seconds=5, loop=True, threaded=False)
def reload_stats():
    linked_players = []
    ingame_players = set()

    for user in conn.execute("SELECT * FROM users").fetchall():
        player = AkatsukiPlayer(
            id=user[0], clan_id=user[1], name=user[2], country=user[3]
        )
        linked_players.append(player)

    # Try to find players that are currently online
    for player in linked_players:
        if bancho_player := game.bancho.players.by_id(player["id"]):
            bancho_player.request_stats()
            ingame_players.add(bancho_player)


def handle_announce(message: str) -> None:
    if "#1 place" in message:
        gamemode_type = message[1:3]
        user_id = 0

        url_beatmap = "[https://osu.akatsuki.gg/beatmaps/"
        url_profile = "[https://akatsuki.gg/u/"
        beatmap_id = 0

        # Parse user_id and beatmap_id
        for string in message.split():
            if string.startswith(url_profile):
                user_id = int(string[len(url_profile) :])

            elif string.startswith(url_beatmap):
                beatmap_id = int(string[len(url_beatmap) :])

        logger.info(f"{user_id} set a #1 on {beatmap_id} ({gamemode_type})")

        # Save to today's #1's
        beatmap = load_beatmap(beatmap_id)
        if not beatmap:
            return
        mode = beatmap["attributes"]["mode"]
        relax = 0
        if beatmap["attributes"]["mode"] == 0:
            player = game.bancho.players.by_id(user_id)
            mode = player.mode.value
        if gamemode_type == "VN":
            relax = 0
        elif gamemode_type == "RX":
            relax = 1
        elif gamemode_type == "AP":
            relax = 2
        gamemode = ""
        for gamemode in gamemodes:
            if gamemodes[gamemode] == {"mode": mode, "relax": relax}:
                break
        cur = conn.cursor()
        exists = cur.execute(
            "SELECT amount FROM leaderboard_user_daily1s WHERE user_id = ? AND date = ? AND gamemode = ?",
            (user_id, str(today()), gamemode),
        ).fetchall()
        if not exists:
            conn.execute(
                "INSERT INTO leaderboard_user_daily1s VALUES (?,?,?,?)",
                (user_id, str(today()), gamemode, 1),
            )
        else:
            conn.execute(
                """UPDATE leaderboard_user_daily1s SET amount = amount+1 WHERE user_id = ? AND date = ? AND gamemode = ?""",
                (user_id, str(today()), gamemode),
            )
        conn.commit()
        # Send event to discord bot
        send_event(
            target="frontend",
            event=first_place_event(user_id, beatmap_id, gamemode),
        )
    else:
        logger.warning(f"Can't handle announce: {message}")


def main():
    try:
        retry = False

        while True:
            game.run(retry, exit_on_interrupt=True)
            game.logger.warning("Restarting...")
            retry = True
    except KeyboardInterrupt:
        exit(0)
