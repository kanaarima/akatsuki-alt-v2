from osu.bancho.constants import ServerPackets
import front.ingamebot.commands as commands
from osu.objects import Player, Channel
from api.logging import get_logger
import front.ingamebot.bot as bot
from typing import Union
from osu import Game


class ClientBackend:
    def __init__(self, username, password, server) -> None:
        self.game = Game(username, password, server=server)
        self.logger = get_logger(f"osu.bot.{server.split('.')[0]}")
        # register anonymous functions
        self.outer_on_message()

    def outer_on_message(self):
        @self.game.events.register(ServerPackets.SEND_MESSAGE)
        def on_message(sender: Player, message: str, target: Union[Player, Channel]):
            if type(target) == Channel:
                pass
                # someday maybe?
                # if target.name == "#announce":
                # self.handle_announce(message)
            elif (message := message.strip()).startswith("!"):
                # Command was executed
                self.logger.info(f"{sender} executed a command: {message}")

                # Parse command
                trigger, *args = message[1:].split()
                trigger = trigger.lower()
                for command in commands.commands:
                    if trigger in command.triggers:
                        command.function(sender, message[1:], args)
                        return

                sender.send_message("Unknown command!")
