from front.commands import user_commands
from api.logging import logger
import api.metrics as metrics
from config import config
import discord


async def handle_command(message: discord.Message):
    full = message.content[len(config["discord"]["bot_prefix"]) :]
    split = full.split(" ")
    metrics.log_command(split[0], full, message, split[0] not in commands)
    if split[0] in commands:
        try:
            await commands[split[0]](full, split[1:], message)
        except:
            logger.error(f"{full} raised an exception!", exc_info=True)
    else:
        await message.reply(content="Unknown command!")


async def ping(full: str, split: list[str], message: discord.Message):
    await message.channel.send(content="pong!")


commands = {
    "ping": ping,
    "link": user_commands.link,
    "recent": user_commands.show_recent,
    "setdefault": user_commands.set_default_gamemode,
    "show": user_commands.show,
    "reset": user_commands.reset,
    "show1s": user_commands.show_1s,
    "showclears": user_commands.show_scores,
}
