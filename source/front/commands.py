from api.objects import LinkedPlayer, Player, gamemodes, gamemodes_full
import api.akatsuki as akatsuki
from api.files import DataFile
from api.utils import get_mods
from config import config
from typing import Tuple
import front.bot as bot
import discord


async def handle_command(message: discord.Message):
    full = message.content[len(config["discord"]["bot_prefix"]) :]
    split = full.split(" ")
    if split[0] in commands:
        await commands[split[0]](full, split, message)
    else:
        await message.reply(content="Unknown command!")


async def ping(full: str, split: list[str], message: discord.Message):
    await message.reply(content="pong!")


async def link(full: str, split: list[str], message: discord.Message):
    if len(split) < 2:
        await message.reply(f"!link username/userID")
        return
    userid = -1
    if split[1].isnumeric():
        userid = int(split[1])
    else:
        userid = akatsuki.lookup_user(" ".join(split[1:]))
        if not userid:
            await message.reply(f"No user matching found. Perhaps use UserID?")
            return
    info = akatsuki.get_user_info(userid)
    if not info:
        await message.reply(f"No user matching found. Perhaps use UserID?")
        return
    file_tracking = DataFile(
        filepath=f"{config['common']['data_directory']}/users_statistics/users.json.gz"
    )
    file_links = DataFile(
        filepath=f"{config['common']['data_directory']}/users_statistics/users_discord.json.gz"
    )
    file_tracking.load_data(default=list())
    file_links.load_data(default={})
    for user in file_tracking.data:
        if user["user_id"] == userid:
            user["full_tracking"] = True
        else:
            file_tracking.data.append(LinkedPlayer(user_id=userid, full_tracking=True))
    file_links.data[str(message.author.id)] = (info, "std")
    file_tracking.save_data()
    file_links.save_data()
    await message.reply(f"Linked successfully.")


async def show_recent(full: str, split: list[str], message: discord.Message):
    player, mode = await _get_linked_account(str(message.author.id))
    if not player:
        await _link_warning(message)
        return
    if len(split) > 1:
        if split[1].lower() in gamemodes:
            mode = split[1].lower()
        else:
            await _wrong_gamemode_warning(message)
            return
    score, map = akatsuki.get_user_recent(userid=player["id"], gamemode=gamemodes[mode])
    if not score:
        await message.reply(f"No recent scores found.")
        return
    score = score[0]
    map = map[0]
    embed = discord.Embed()
    embed.set_author(
        name=f"{player['name']} on {gamemodes_full[mode]}",
        icon_url=f"https://a.akatsuki.gg/{player['id']}",
    )
    embed.set_image(
        url=f"https://assets.ppy.sh/beatmaps/{map['beatmap_set_id']}/covers/cover@2x.jpg"
    )
    embed.add_field(name="Artist", value=map["artist"])
    embed.add_field(name="Title", value=map["title"])
    embed.add_field(name="Difficulty", value=map["difficulty"])
    embed.add_field(
        name="Star Rating", value=f"{map['star_rating']}"
    )  # TODO: include other types
    embed.add_field(name="OD", value=map["od"])
    embed.add_field(name="AR", value=map["ar"])
    embed.add_field(
        name="300/100/50/X",
        value=f"{score['count_300']}/{score['count_100']}/{score['count_50']}/{score['count_miss']}",
    )
    embed.add_field(name="score", value=f"{score['score']:,}")
    embed.add_field(name="pp", value=f"{score['pp']:,}")
    embed.add_field(name="mods", value=f"{''.join(get_mods(score['mods']))}")
    embed.add_field(name="combo", value=score["combo"])
    embed.add_field(name="download", value=_get_download_link(map["beatmap_id"]))
    await message.reply(embed=embed)


async def _get_linked_account(discord_id: str) -> Tuple[Player, str]:
    file_links = DataFile(
        filepath=f"{config['common']['data_directory']}/users_statistics/users_discord.json.gz"
    )
    file_links.load_data(default={})
    if discord_id not in file_links.data:
        return None, None, None
    return file_links.data[discord_id]


async def _link_warning(message: discord.Message):
    await message.reply(f"You don't have an account linked! use !link username/userID.")


async def _wrong_gamemode_warning(message: discord.Message):
    await message.reply(f"Invalid gamemode! Valid gamemodes: {gamemodes.keys()}")


def _get_download_link(beatmap_id: int):
    return f"[direct](https://towwyyyy.marinaa.nl/osu/osudl.html?beatmap={beatmap_id}) [bancho](https://osu.ppy.sh/b/{beatmap_id})"


commands = {"ping": ping, "link": link, "recent": show_recent}
