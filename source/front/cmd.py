from front.commands import user_commands, debug_commands
from api.logging import get_logger
import api.metrics as metrics
from config import config
import discord
import shlex

logger = get_logger("discord.bot")
PRIVILEDGES = {"dev": 0, "trusted": 1, "user": 2}


async def handle_command(message: discord.Message):
    full = message.content[len(config["discord"]["bot_prefix"]) :]
    split = shlex.split(full.lower())
    metrics.log_command(split[0], full, message, split[0] not in commands)
    if split[0] in commands:
        try:
            await commands[split[0]](full, split[1:], message)
        except:
            logger.error(f"{full} raised an exception!", exc_info=True)
            await message.reply("An error occurred while running this command!")
    else:
        await message.reply(content="Unknown command!")


async def ping(full: str, split: list[str], message: discord.Message):
    await message.channel.send(content="pong!")


async def authorized(message: discord.Message, auth_level=0):
    if check_priviledges(message.author.roles) > auth_level:
        await message.reply("You don't have permissions to do that.")
        return False
    return True


def check_priviledges(roles: list[discord.Role]):
    priviledge = 4
    for role in roles:
        if role.id in config["discord"]["dev_roles"]:
            priviledge = 0
        elif role.id in config["discord"]["trusted_roles"]:
            priviledge = min(priviledge, 1)
        elif role.id in config["discord"]["members"]:
            priviledge = min(priviledge, 2)
    return priviledge


commands = {
    "ping": ping,
    "link": user_commands.link,
    "recent": user_commands.show_recent,
    "setdefault": user_commands.set_default_gamemode,
    "show": user_commands.show,
    "reset": user_commands.reset,
    "show1s": user_commands.show_1s,
    "showclears": user_commands.show_scores,
    "showcompletion": user_commands.show_scores_completion,
    "checkbeatmaptype": debug_commands.check_beatmap_type,
}
