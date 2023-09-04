from api.utils import str_to_datetime, datetime_to_str, yesterday, other_yesterday
from front.leaderboards import clan_leaderboards, user_leaderboards
from api.objects import gamemodes_full
from front.views import get_score_embed
from api.files import DataFile
from api.logging import logger
import api.akatsuki as akatsuki
import api.beatmaps as beatmaps
from datetime import datetime
from discord.ext import tasks
from config import config
from front import bot
import api.events
import subprocess
import requests
import discord
import asyncio
import glob
import io


async def post_list(channel_id, strings):
    str = "```"
    for string in strings[:100]:
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
            logger.warning(f"{key} not found!")
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
        player_new=player_file.data, player_old=player_old_file.data
    )
    for key in lists.keys():
        if key not in config["discord"]["channels"]:
            logger.warning(f"{key} not found!")
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


@tasks.loop(minutes=2)
async def refresh_status():
    try:
        msg = await bot.client.get_channel(
            config["discord"]["status_update"]["channel_id"]
        ).fetch_message(config["discord"]["status_update"]["message_id"])
        if msg:
            status_data = DataFile(
                f"{config['common']['log_directory']}/status.json.gz"
            )
            status_data.load_data()
            maps_path = f"{config['common']['data_directory']}/beatmaps"
            update_embed = discord.Embed(title="Service status")
            tasks_status = ""
            for task, status in status_data.data.items():
                tasks_status += f"{task}: {status}\n"
            if not tasks_status:
                tasks_status = "No tasks currently running."
            update_embed.add_field(name="Backend operations", value=tasks_status)
            size = (
                subprocess.check_output(["du", "-sh", maps_path])
                .split()[0]
                .decode("utf-8")
            )
            maps_processed = len(glob.glob(f"{maps_path}/*.json.gz"))
            maps_downloaded = len(glob.glob(f"{maps_path}/*.osu.gz"))
            update_embed.add_field(
                name="Maps info",
                value=f"Processed: {maps_processed}\nDownloaded: {maps_downloaded}\nSize: {size}",
            )
            update_embed.set_footer(text=f"Last updated: {datetime.now()}")
            await msg.edit(content="", embed=update_embed)
    except:
        pass


@tasks.loop(seconds=10)
async def handle_events():
    try:
        events = api.events.read_events("frontend")
        for event in events:
            if event["name"] == "ChannelMessageEvent":
                message_event: api.events.ChannelMessageEvent = event
                if message_event["channel"] in config["discord"]["forward_channels"]:
                    await bot.client.get_channel(
                        config["discord"]["forward_channels"][message_event["channel"]]
                    ).send(content=message_event["message"], suppress_embeds=True)
            elif event["name"] == "TopPlayEvent":
                top_play_event: api.events.TopPlayEvent = event
                beatmap = beatmaps.load_beatmap(top_play_event["beatmap_id"])
                if not beatmap:  # should be unnecessary
                    continue
                replay = get_replay(top_play_event["score"]["id"])
                player = akatsuki.get_user_info(top_play_event["user_id"])
                title = f"{player['name']} set a new {gamemodes_full[top_play_event['gamemode']]} top play! (#{top_play_event['index']})"
                embed = get_score_embed(
                    player=player,
                    beatmap=beatmap,
                    score=top_play_event["score"],
                    title_overwrite=title,
                    use_thumbnail=False,
                )
                await bot.client.get_channel(config["discord"]["render_channel"]).send(
                    embed=embed
                )
                if replay:
                    channel = bot.client.get_channel(
                        config["discord"]["render_channel"]
                    )
                    webhook = await channel.create_webhook(name="Replay fetcher")
                    await webhook.send(
                        file=discord.File(
                            fp=replay, filename=f"{top_play_event['score']['id']}.osr"
                        )
                    )
                    await webhook.delete()
    except:
        logger.error("Could not handle events!", exc_info=True)


@tasks.loop(minutes=1)
async def cleanup_render_channel():
    channel = bot.client.get_channel(config["discord"]["render_channel"])
    history = channel.history(limit=100)
    async for message in history:
        try:
            if message.author.id == bot.client.user.id:
                continue
            if message.attachments:
                continue
            if "https://" in message.content:
                await channel.send(content=message.content.split()[1])
            await message.delete()
            await asyncio.sleep(1)
        except:
            continue


def get_replay(scoreid):
    req = requests.get(
        f"https://akatsuki.gg/web/replays/{scoreid}", allow_redirects=True
    )
    if req.status_code != 200:  # 404?
        return
    return io.BytesIO(req.content)


def init_tasks():
    post_lb_updates.start()
    refresh_status.start()
    handle_events.start()
    cleanup_render_channel.start()
