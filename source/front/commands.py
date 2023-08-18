from api.objects import (
    LinkedPlayer,
    Player,
    GamemodeStatistics,
    Ranking,
    gamemodes,
    gamemodes_full,
)
import api.akatsuki as akatsuki
from api.files import DataFile, exists
from api.utils import get_mods, yesterday
from typing import List, Tuple, Dict
from config import config
import front.bot as bot
from front.views import ScoresView
import datetime
import discord


async def handle_command(message: discord.Message):
    full = message.content[len(config["discord"]["bot_prefix"]) :]
    split = full.split(" ")
    if split[0] in commands:
        await commands[split[0]](full, split[1:], message)
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
            break
    else:
        file_tracking.data.append(LinkedPlayer(user_id=userid, full_tracking=True))
    file_links.data[str(message.author.id)] = (info, "std")
    file_tracking.save_data()
    file_links.save_data()
    await message.reply(f"Linked successfully.")


async def set_default_gamemode(full: str, split: list[str], message: discord.Message):
    if len(split) < 2:
        await message.reply("!setdefault gamemode")
        return
    discord_id = str(message.author.id)
    file_links = DataFile(
        filepath=f"{config['common']['data_directory']}/users_statistics/users_discord.json.gz"
    )
    file_links.load_data(default={})
    if discord_id not in file_links.data:
        await _link_warning(message)
        return
    mode = split[1].lower()
    if mode not in gamemodes:
        await _wrong_gamemode_warning(message)
        return
    file_links.data[discord_id][1] = mode
    file_links.save_data()
    await message.reply(f"Default gamemode set to {gamemodes_full[mode]}")


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


async def show(full: str, split: list[str], message: discord.Message):
    player, gamemode = await _get_linked_account(str(message.author.id))
    if not player:
        await _link_warning()
        return
    user_file = DataFile(
        f"{config['common']['data_directory']}/users_statistics/temp/{player['id']}.json.gz"
    )
    user_file.load_data(default=[])
    _update_fetch(player, user_file)
    user_file.save_data()
    recent: Dict[str, Tuple[GamemodeStatistics, Ranking, Ranking]] = user_file.data[-1][
        1
    ]
    oldest: Dict[str, Tuple[GamemodeStatistics, Ranking, Ranking]] = user_file.data[0][
        1
    ]
    embed = discord.Embed(
        colour=discord.Color.og_blurple(),
        title=f"Stats for {player['name']}",
    )
    embed.set_thumbnail(
        url=f"https://a.akatsuki.gg/{player['id']}",
    )
    global_rank_gain = _format_gain_string(
        oldest[gamemode][2]["global_ranking"] - recent[gamemode][2]["global_ranking"]
    )
    global_score_rank_gain = _format_gain_string(
        oldest[gamemode][1]["global_ranking"] - recent[gamemode][1]["global_ranking"]
    )
    country_rank_gain = _format_gain_string(
        oldest[gamemode][2]["country_ranking"] - recent[gamemode][2]["country_ranking"]
    )
    country_score_rank_gain = _format_gain_string(
        oldest[gamemode][1]["country_ranking"] - recent[gamemode][1]["country_ranking"]
    )

    ranked_score_gain = _format_gain_string(
        recent[gamemode][0]["ranked_score"] - oldest[gamemode][0]["ranked_score"]
    )
    total_score_gain = _format_gain_string(
        recent[gamemode][0]["total_score"] - oldest[gamemode][0]["total_score"]
    )
    total_hits_gain = _format_gain_string(
        recent[gamemode][0]["total_hits"] - oldest[gamemode][0]["total_hits"]
    )
    play_count_gain = _format_gain_string(
        recent[gamemode][0]["play_count"] - oldest[gamemode][0]["play_count"]
    )
    play_time_gain = _format_gain_string(
        recent[gamemode][0]["play_time"] / 60 - oldest[gamemode][0]["play_time"] / 60,
        fix="min",
    )
    replay_gain = _format_gain_string(
        recent[gamemode][0]["watched_replays"] - oldest[gamemode][0]["watched_replays"]
    )
    level_gain = _format_notation(
        recent[gamemode][0]["level"] - oldest[gamemode][0]["level"]
    )
    acc_gain = _format_gain_string(
        recent[gamemode][0]["profile_accuracy"]
        - oldest[gamemode][0]["profile_accuracy"]
    )
    max_combo_gain = _format_gain_string(
        recent[gamemode][0]["max_combo"] - oldest[gamemode][0]["max_combo"]
    )
    pp_gain = _format_gain_string(
        recent[gamemode][0]["total_pp"] - oldest[gamemode][0]["total_pp"]
    )
    fp_gain = _format_gain_string(
        recent[gamemode][0]["total_1s"] - oldest[gamemode][0]["total_1s"]
    )

    embed.add_field(
        name="Ranked score",
        value=f"{recent[gamemode][0]['ranked_score']:,}\n{ranked_score_gain}",
    )
    embed.add_field(
        name="Total score",
        value=f"{recent[gamemode][0]['total_score']:,}\n{total_score_gain}",
    )
    embed.add_field(
        name="Total hits",
        value=f"{recent[gamemode][0]['total_hits']:,}\n{total_hits_gain}",
    )
    embed.add_field(
        name="Play count",
        value=f"{recent[gamemode][0]['play_count']:,}\n{play_count_gain}",
    )
    embed.add_field(
        name="Play time",
        value=f"{recent[gamemode][0]['play_time']/60/60:,.2f}h\n{play_time_gain}",
    )
    embed.add_field(
        name="Replays watched",
        value=f"{recent[gamemode][0]['watched_replays']}\n{replay_gain}",
    )
    embed.add_field(
        name="Level",
        value=f"{recent[gamemode][0]['level']:.4f}\n{level_gain}",
    )
    embed.add_field(
        name="Accuracy",
        value=f"{recent[gamemode][0]['profile_accuracy']:,.2f}%\n{acc_gain}",
    )

    embed.add_field(
        name="Max combo",
        value=f"{recent[gamemode][0]['max_combo']:,}x\n{max_combo_gain}",
    )
    embed.add_field(
        name="Global rank",
        value=f"#{recent[gamemode][2]['global_ranking']:,}\n{global_rank_gain}",
    )
    embed.add_field(
        name="Country rank",
        value=f"#{recent[gamemode][2]['country_ranking']:,}\n{country_rank_gain}",
    )
    embed.add_field(
        name="Performance points",
        value=f"{recent[gamemode][0]['total_pp']:,}pp\n{pp_gain}",
    )
    embed.add_field(
        name="Global score rank",
        value=f"#{recent[gamemode][1]['global_ranking']:,}\n{global_score_rank_gain}",
    )
    embed.add_field(
        name="Country score rank",
        value=f"#{recent[gamemode][1]['country_ranking']:,}\n{country_score_rank_gain}",
    )
    embed.add_field(
        name="#1 count", value=f"{recent[gamemode][0]['total_1s']:,}\n{fp_gain}"
    )
    await message.reply(embed=embed)


async def show_1s(full: str, split: list[str], message: discord.Message):
    player, gamemode = await _get_linked_account(str(message.author.id))
    if not player:
        await _link_warning()
        return
    args = _parse_args(split)
    if "default" in args:
        gamemode = args["default"].lower()
        if gamemode not in gamemodes:
            await _wrong_gamemode_warning(message)
            return
    path = f"{config['common']['data_directory']}/users_statistics/{yesterday()}/{player['id']}.json.gz"
    if not exists(path):
        await message.reply(f"Your statistics aren't fetched yet. Please wait!")
        return
    file = DataFile(path)
    file.load_data()
    scores = file.data["first_places"][gamemode]
    view = ScoresView(
        f"{player['name']}'s {gamemodes_full[gamemode]} first places ({len(scores):,})",
        scores,
    )
    await view.reply(message)


async def reset(full: str, split: list[str], message: discord.Message):
    player, _ = await _get_linked_account(str(message.author.id))
    if not player:
        await _link_warning()
        return
    user_file = DataFile(
        f"{config['common']['data_directory']}/users_statistics/temp/{player['id']}.json.gz"
    )
    user_file.load_data(default=[])
    _update_fetch(player, user_file)
    user_file.data = [user_file.data[-1]]
    await message.reply("Data resetted.")


async def _get_linked_account(discord_id: str) -> Tuple[Player, str]:
    file_links = DataFile(
        filepath=f"{config['common']['data_directory']}/users_statistics/users_discord.json.gz"
    )
    file_links.load_data(default={})
    if discord_id not in file_links.data:
        return None, None
    return file_links.data[discord_id]


async def _link_warning(message: discord.Message):
    await message.reply(f"You don't have an account linked! use !link username/userID.")


async def _wrong_gamemode_warning(message: discord.Message):
    await message.reply(f"Invalid gamemode! Valid gamemodes: {gamemodes.keys()}")


def _get_download_link(beatmap_id: int):
    return f"[direct](https://towwyyyy.marinaa.nl/osu/osudl.html?beatmap={beatmap_id}) [bancho](https://osu.ppy.sh/b/{beatmap_id})"


def _update_fetch(player: Player, user_file: DataFile):
    for fetch in user_file.data:
        date = datetime.datetime.strptime(fetch[0], "%d/%m/%Y %H:%M:%S")
        if (datetime.datetime.now() - date) > datetime.timedelta(hours=24):
            user_file.data.remove(fetch)

    if not user_file.data:
        user_file.data.append(
            (
                datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                akatsuki.get_user_stats(player["id"])[1],
            )
        )
    date = datetime.datetime.strptime(user_file.data[-1][0], "%d/%m/%Y %H:%M:%S")
    if (datetime.datetime.now() - date) > datetime.timedelta(minutes=5):
        user_file.data.append(
            (
                datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                akatsuki.get_user_stats(player["id"])[1],
            )
        )


def _format_gain_string(gain, fix=""):
    is_float = type(gain) == float
    if gain == 0:
        return ""
    if gain > 1:
        return f"(+{gain:,.2f}{fix})" if is_float else f"(+{gain:,}{fix})"
    else:
        return f"({gain:,.2f}{fix})" if is_float else f"({gain:,}{fix})"


def _format_notation(gain):
    if gain == 0:
        return ""
    return f"({gain:.2e})"


def _parse_args(args: List[str]) -> dict:
    parsed = {}
    for arg in args:
        s = arg.split("=")
        if len(s) == 1:
            if "default" in parsed:
                parsed[arg] = ""
            else:
                parsed["default"] = arg
        else:
            parsed[s[0]] = s[1]
    return parsed


commands = {
    "ping": ping,
    "link": link,
    "recent": show_recent,
    "setdefault": set_default_gamemode,
    "show": show,
    "reset": reset,
    "show1s": show_1s,
}
