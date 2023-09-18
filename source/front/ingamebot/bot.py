from front.ingamebot.backends.akatsuki import AkatsukiBackend
from front.ingamebot.backends.client import ClientBackend
from api.logging import get_logger
from threading import Thread
from config import config
from osu import Game

logger = get_logger("osu.bot")


def game_thread_loop(backend):
    try:
        retry = False
        while True:
            backend.game.run(retry, exit_on_interrupt=True)
            backend.game.logger.warning("Restarting...")
            retry = True
    except KeyboardInterrupt:
        exit(0)


def main():
    threads = []
    backends = [
        AkatsukiBackend(
            config["bot_account"]["username"], config["bot_account"]["password"]
        )
    ]
    for profile in config["bot_servers"]:
        backends.append(
            ClientBackend(profile["username"], profile["password"], profile["server"])
        )
    for backend in backends:
        thread = Thread(target=game_thread_loop, args=(backend,), daemon=True)
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
