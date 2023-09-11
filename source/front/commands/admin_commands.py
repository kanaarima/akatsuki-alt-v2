from front.commands.user_commands import _parse_args
import api.beatmaps as beatmaps
import api.database as database
from config import config
import discord
import io

PRIVILEDGES = {"dev": 0, "trusted": 1, "user": 2}


async def insert_beatmap(full: str, split: list[str], message: discord.Message):
    if not await authorized(message, auth_level=1):
        return
    args = _parse_args(split)
    if "default" not in args or not args["default"].isnumeric():
        await message.reply("specify a beatmap id.")
        return
    beatmap = beatmaps.load_beatmap(beatmap_id=int(args["default"]))
    beatmaps.process_beatmap(beatmap)
    if "status" not in beatmap:
        await message.reply(f"map cant be found.")
        return
    await message.reply(f"Force updated {beatmap['beatmap_id']} ({beatmap['title']})")


async def query(full: str, split: list[str], message: discord.Message):
    if not await authorized(message, auth_level=0):
        return
    query = " ".join(split)
    cur = database.conn_uri.cursor()
    check = cur.execute(query)
    string = "\n".join([repr(item) for item in check.fetchall()])
    cur.close()
    await message.reply(
        file=discord.File(io.BytesIO(bytes(string, "utf-8")), filename="query.txt")
    )


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
