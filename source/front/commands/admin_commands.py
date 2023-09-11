from config import config
import discord

PRIVILEDGES = {"dev": 0, "trusted": 1, "user": 2}


async def insert_beatmap(full: str, split: list[str], message: discord.Message):
    if not await authorized(message, auth_level=1):
        return
    await message.reply("pong")


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
        elif role.id in config["discord"]["member_roles"]:
            priviledge = min(priviledge, 2)
    return priviledge
