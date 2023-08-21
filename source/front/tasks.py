from api.utils import str_to_datetime, datetime_to_str, yesterday, other_yesterday
from front.leaderboards import clan_leaderboards, user_leaderboards
from api.files import DataFile
from datetime import datetime
from discord.ext import tasks
from config import config
from front import bot
import asyncio


async def post_list(channel_id, strings):
    str = "```"
    for string in strings:
        str += f"{string}\n"
        if len(str) > 1900:
            str += "```"
            await bot.client.get_channel(channel_id).send(content=str)
            await asyncio.sleep(1)
            str = "```"
    str += "```"
    if str != "```":
        await bot.client.get_channel(channel_id).send(content=str)
    await asyncio.sleep(1)


async def post_clan_updates():
    clan_file = DataFile(
        f"{config['common']['data_directory']}/leaderboards/clans/{yesterday()}.json.gz"
    )
    clan_old_file = DataFile(
        f"{config['common']['data_directory']}/leaderboards/clans/{other_yesterday()}.json.gz"
    )
    if not await clan_file.wait_till_exist(timeout=180):
        return
    if not clan_old_file.exists():
        clan_old_file = clan_file
    clan_file.load_data()
    clan_old_file.load_data()
    lists = clan_leaderboards.generate_clan_leaderboards(
        clan_new=clan_file.data, clan_old=clan_old_file.data
    )
    for key in lists.keys():
        if key not in config["discord"]["channels"]:
            print(f"{key} not found!")
            continue
        await post_list(config["discord"]["channels"][key], lists[key][:100])


async def post_user_updates():
    player_file = DataFile(
        f"{config['common']['data_directory']}/leaderboards/users/{yesterday()}.json.gz"
    )
    player_old_file = DataFile(
        f"{config['common']['data_directory']}/leaderboards/users/{other_yesterday()}.json.gz"
    )
    if not await player_file.wait_till_exist(timeout=180):
        return
    if not player_old_file.exists():
        player_old_file = player_file
    player_file.load_data()
    player_old_file.load_data()
    lists = user_leaderboards.generate_user_leaderboards(
        player_new=player_file.data, player_old=player_file.data
    )
    for key in lists.keys():
        if key not in config["discord"]["channels"]:
            print(f"{key} not found!")
            continue
        await post_list(config["discord"]["channels"][key], lists[key])


@tasks.loop(minutes=10)
async def post_lb_updates():
    file = DataFile(f"{config['common']['data_directory']}/poster.json.gz")
    file.load_data(
        default={"last_posted": datetime_to_str(datetime(year=2000, month=1, day=1))}
    )
    date = str_to_datetime(file.data["last_posted"])
    if date.day == datetime.now().day:
        return
    file.data["last_posted"] = datetime_to_str(datetime.now())
    file.save_data()
    await post_clan_updates()
    await post_user_updates()


def init_tasks():
    post_lb_updates.start()
