from api.utils import (
    get_mods_simple,
    yesterday,
    other_yesterday,
    convert_mods,
    datetime_to_str,
    today,
    get_mods,
    mods_from_string,
    score_from_db,
)
from front.views import (
    ScoresView,
    ScoreDiffView,
    StringListView,
    get_score_embed,
    get_help_view,
)
from front.commands.help import help
from api.collections import generate_collection
from api.files import DataFile, exists
from typing import List, Tuple, Dict
import api.beatmaps as beatmaps
import api.akatsuki as akatsuki
import api.database as database
import api.farmerv2 as farmerv2
import api.farmer as farmer
from config import config
from api.objects import *
import datetime
import discord
import io
import re


async def link(full: str, split: list[str], message: discord.Message):
    if not split:
        await message.reply("!link username/userID")
        return
    userid = -1
    if split[0].isnumeric():
        userid = int(split[0])
    else:
        userid = akatsuki.lookup_user(" ".join(split))
        if not userid:
            await message.reply("No user matching found. Perhaps use UserID?")
            return
    info = akatsuki.get_user_stats(userid, no_1s=True)[0]
    if not info:
        await message.reply("No user matching found. Perhaps use UserID?")
        return
    c = database.ConnectionHandler()
    check = c.execute(
        "SELECT user_id FROM users WHERE discord_id = ?", (message.author.id,)
    ).fetchone()
    if check:
        await message.reply("You can't link twice!")
    else:
        c.execute(
            "INSERT INTO users VALUES(?,?,?,?,?,?)",
            (
                info["id"],
                info["clan_id"],
                info["name"],
                info["country"],
                message.author.id,
                "std",
            ),
        )
        await message.reply("Linked successfully.")
    c.close()


async def set_default_gamemode(full: str, split: list[str], message: discord.Message):
    if not split:
        await message.reply("!setdefault gamemode")
        return
    c = database.ConnectionHandler()
    check = c.execute(
        "SELECT user_id FROM users WHERE discord_id = ?", (message.author.id,)
    ).fetchone()
    if not check:
        await _link_warning(message)
        return
    mode = split[0].lower()
    if mode not in gamemodes:
        await _wrong_gamemode_warning(message)
        return
    c.execute(
        """UPDATE users SET "default_mode" = ? WHERE discord_id = ?""",
        (mode, message.author.id),
    )
    c.close()
    await message.reply(f"Default gamemode set to {gamemodes_full[mode]}")


async def show_recent(full: str, split: list[str], message: discord.Message):
    player, mode = await _get_linked_account(str(message.author.id))
    if not player:
        await _link_warning(message)
        return
    if split:
        if split[0].lower() in gamemodes:
            mode = split[0].lower()
        else:
            await _wrong_gamemode_warning(message)
            return
    score, map = akatsuki.get_user_recent(userid=player["id"], gamemode=gamemodes[mode])
    if not score:
        await message.reply("No recent scores found.")
        return
    score = score[0]
    map = map[0]
    # Process map
    beatmaps.save_beatmap(map)
    map = beatmaps.load_beatmap(map["beatmap_id"], difficulty_info=True)
    await message.reply(embed=get_score_embed(player=player, beatmap=map, score=score))


async def show(full: str, split: list[str], message: discord.Message):
    player, gamemode = await _get_linked_account(str(message.author.id))
    if not player:
        await _link_warning(message)
        return
    user_file = DataFile(
        f"{config['common']['data_directory']}/users_statistics/temp/{player['id']}.json.gz"
    )
    user_file.load_data(default=[])
    _update_fetch(player, user_file)
    user_file.save_data()
    args = _parse_args(split)
    if "default" in args:
        gamemode = args["default"].lower()
        if gamemode not in gamemodes:
            await _wrong_gamemode_warning(message)
            return

    recent: Dict[str, Tuple[GamemodeStatistics, Ranking, Ranking]] = user_file.data[-1][
        1
    ]
    oldest: Dict[str, Tuple[GamemodeStatistics, Ranking, Ranking]] = user_file.data[0][
        1
    ]
    if "compareto" in args:
        path = f"{config['common']['data_directory']}/users_statistics/{args['compareto']}/{player['id']}.json.gz"
        if not exists(path):
            await message.reply("You don't have stats recorded for that day!")
            return
        oldfile = DataFile(path)
        oldfile.load_data()
        oldest = oldfile.data["statistics"]
        if "total_score_rank" not in oldest:
            oldest[gamemode][0]["total_score_rank"] = Ranking(
                global_ranking=0, country_ranking=0
            )
            oldest[gamemode][0]["clears"] = 0
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
    global_total_score_rank_gain = _format_gain_string(
        oldest[gamemode][0]["total_score_rank"]["global_ranking"]
        - recent[gamemode][0]["total_score_rank"]["global_ranking"]
    )
    country_rank_gain = _format_gain_string(
        oldest[gamemode][2]["country_ranking"] - recent[gamemode][2]["country_ranking"]
    )
    country_score_rank_gain = _format_gain_string(
        oldest[gamemode][1]["country_ranking"] - recent[gamemode][1]["country_ranking"]
    )
    country_total_score_rank_gain = _format_gain_string(
        oldest[gamemode][0]["total_score_rank"]["country_ranking"]
        - recent[gamemode][0]["total_score_rank"]["country_ranking"]
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
    clears_gain = _format_gain_string(
        recent[gamemode][0]["clears"] - oldest[gamemode][0]["clears"]
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
    embed.add_field(
        name="Global t.score rank",
        value=f"#{recent[gamemode][0]['total_score_rank']['global_ranking']:,}\n{global_total_score_rank_gain}",
    )
    embed.add_field(
        name="Country t.score rank",
        value=f"#{recent[gamemode][0]['total_score_rank']['country_ranking']:,}\n{country_total_score_rank_gain}",
    )
    embed.add_field(
        name="Clears",
        value=f"{recent[gamemode][0]['clears']:,}\n{clears_gain}",
    )
    await message.reply(embed=embed)


async def show_1s(full: str, split: list[str], message: discord.Message):
    player, gamemode = await _get_linked_account(str(message.author.id))
    if not player:
        await _link_warning(message)
        return
    new = False
    args = _parse_args(split)
    if "default" in args:
        if args["default"].lower() == "new":
            new = True
        else:
            gamemode = args["default"].lower()
            if gamemode not in gamemodes:
                await _wrong_gamemode_warning(message)
                return
    if "new" in args:
        new = True
    path = f"{config['common']['data_directory']}/users_statistics/{yesterday()}/{player['id']}.json.gz"
    if not exists(path):
        await message.reply("Your statistics aren't fetched yet. Please wait!")
        return
    file = DataFile(path)
    file.load_data()
    scores = file.data["first_places"][gamemode]
    _, new_1s, new_maps = akatsuki.get_user_1s(player["id"], gamemodes[gamemode])
    beatmaps.save_beatmaps(new_maps)
    broke = False
    for newscore in new_1s:
        for oldscore in scores:
            if oldscore["id"] == newscore["id"]:
                broke = True
                break
        else:
            scores.append(newscore)
        if broke:
            break
    if new:
        path_old = f"{config['common']['data_directory']}/users_statistics/{other_yesterday()}/{player['id']}.json.gz"
        if not exists(path_old):
            await message.reply("Your statistics aren't fetched yet. Please wait!")
            return
        file = DataFile(path_old)
        file.load_data()
        scores_old = file.data["first_places"][gamemode]
        view = ScoreDiffView(
            f"{player['name']}'s {gamemodes_full[gamemode]} first places changes",
            scores_old=scores_old,
            scores_new=scores,
        )
    else:
        view = ScoresView(
            f"{player['name']}'s {gamemodes_full[gamemode]} first places ({len(scores):,})",
            scores,
        )
    await view.reply(message)


async def reset(full: str, split: list[str], message: discord.Message):
    player, _ = await _get_linked_account(str(message.author.id))
    if not player:
        await _link_warning(message)
        return
    user_file = DataFile(
        f"{config['common']['data_directory']}/users_statistics/temp/{player['id']}.json.gz"
    )
    user_file.load_data(default=[])
    _update_fetch(player, user_file)
    user_file.data = [user_file.data[-1]]
    user_file.save_data()
    await message.reply("Data resetted.")


async def show_scores(full: str, split: list[str], message: discord.Message):
    player, gamemode = await _get_linked_account(str(message.author.id))
    if not player:
        await _link_warning(message)
        return
    args = _parse_args(split)
    if "default" in args:
        gamemode = args["default"].lower()
        if gamemode not in gamemodes:
            await _wrong_gamemode_warning(message)
            return
    view = "all"
    if "view" in args:
        valid_types = [
            "ranked_bancho",
            "ranked_akatsuki",
            "qualified_bancho",
            "loved_bancho",
            "loved_akatsuki",
            "unranked",
        ]
        if args["view"].lower() not in valid_types:
            await message.reply(f"Invalid view! {','.join(valid_types)}")
            return
        view = args["view"]
    cur = database.ConnectionHandler()
    scores = cur.execute(
        "SELECT * FROM users_scores WHERE user_id = ? AND mode = ?",
        (player["id"], gamemode),
    ).fetchall()
    cur.close()
    if not scores:
        await message.reply("Your statistics aren't fetched yet. Please wait!")
        return
    scores = [score_from_db(score) for score in scores]
    if view != "all":
        cache = beatmaps.get_by_leaderboard(leaderboards=[view])[view]
        new_scores = [score for score in scores if int(score["beatmap_id"]) in cache]
        scores = new_scores
    view = ScoresView(
        f"{player['name']}'s {gamemodes_full[gamemode]} scores ({len(scores):,})",
        list(scores),
    )
    await view.reply(message)


async def show_scores_completion(full: str, split: list[str], message: discord.Message):
    player, gamemode = await _get_linked_account(str(message.author.id))
    gamemode = "std_rx"
    if not player:
        await _link_warning(message)
        return
    args = _parse_args(split, nodefault=True)
    type = "ranked_bancho"
    viewtype = "info"
    valid_types = ["ranked_bancho", "ranked_akatsuki", "loved_bancho", "loved_akatsuki"]
    include_all = "completed" not in args
    tags = None
    artists = None
    mappers = None
    if "type" in args:
        if args["type"].lower() not in valid_types:
            await message.reply(f"Invalid type! {','.join(valid_types)}")
            return
        type = args["type"].lower()
    if "view" in args:
        valid_views = ["info", "maps", "maps_missing"]
        if args["view"].lower() not in valid_views:
            await message.reply(f"Invalid view! {','.join(valid_views)}")
            return
        viewtype = args["view"].lower()
    if "tags" in args:
        tags = args["tags"].split(",")
    if "artists" in args:
        artists = args["artists"].split(",")
    if "mappers" in args:
        mappers = args["mappers"].split(",")
    path = f"{config['common']['data_directory']}/users_statistics/scores/{player['id']}.json.gz"
    if not exists(path):
        await message.reply("Your statistics aren't fetched yet. Please wait!")
        return
    cache = beatmaps.get_completion_cache(leaderboards=valid_types)
    file = DataFile(path)
    file.load_data()
    lists = {}
    scores = file.data[gamemode]
    title = "Statistics"
    filtered = []
    beatmap_tags = {}
    filters = 0
    if tags:
        filters += 1
        for key in valid_types:
            for tag in cache[key]["tags"]:
                if tag.lower() in tags:
                    filtered.extend(cache[key]["tags"][tag])
    if artists:
        filters += 1
        for key in valid_types:
            for artist in cache[key]["artists"]:
                if artist.lower() in artists:
                    filtered.extend(cache[key]["artists"][artist])
    if mappers:
        filters += 1
        for key in valid_types:
            for mapper in cache[key]["mappers"]:
                if mapper.lower() in mappers:
                    filtered.extend(cache[key]["mappers"][mapper])
    if filters > 1:
        found = {}
        for id in filtered:
            if id in found:
                found[id] += 1
            else:
                found[id] = 1
        filtered = []
        for k, v in found.items():
            if v == filters:
                filtered.append(k)

    def is_allowed(id):
        return id in filtered if filtered else True

    def is_key_allowed(key):
        if key == "total":
            return False
        if not filtered:
            return True
        valid = False
        if tags and key == "tags":
            valid = True
        if artists and key == "artists":
            valid = True
        if mappers and key == "mappers":
            valid = True
        return valid

    if "generate" in args:
        if not filtered:
            await message.reply(
                "You need to use filtering options first! (artists,mappers,tags)"
            )
            return
        if len(filtered) > 10000:
            await message.reply("Too many maps!")
            return
        maps: List[Beatmap] = []
        csv = "beatmap_set_id,beatmap_id,artist,title,difficulty_name,mapper,status_bancho,status_akatsuki\n"
        for id in filtered:
            beatmap = beatmaps.load_beatmap(id)
            if beatmap:
                maps.append(beatmap)
        for map in maps:
            csv += f"{map['beatmap_set_id']},{map['beatmap_id']},{map['artist']},{map['title']},{map['difficulty_name']},{map['mapper']},{map['status']['bancho']},{map['status']['akatsuki']}\n"
        name = "Automated collection"
        if "name" in args:
            name = args["name"]
        filepath = f"{config['common']['cache_directory']}/{message.author.id}.osdb"
        generate_collection(maps, name, filepath)
        await message.reply(
            files=[
                discord.File(fp=filepath, filename="collection.osdb"),
                discord.File(io.BytesIO(bytes(csv, "utf-8")), filename="beatmaps.csv"),
            ]
        )
        return
    elif viewtype == "info":
        lists["Completion"] = []
        for key in valid_types:
            total = len(cache[key]["total"])
            found = sum(1 for id in cache[key]["total"] if str(id) in scores)
            lists["Completion"].append(
                f"{key}: {found}/{total} ({(found/total)*100:.2f}%)"
            )
        for key in cache[type].keys():
            if not is_key_allowed(key):
                continue
            lists[key] = []
            for list_key in cache[type][key].keys():
                if tags and key == "tags" and list_key.lower() not in tags:
                    continue
                if artists and key == "artists" and list_key.lower() not in artists:
                    continue
                if mappers and key == "mappers" and list_key.lower() not in mappers:
                    continue
                all = len(cache[type][key][list_key])
                found = sum(1 for id in cache[type][key][list_key] if str(id) in scores)
                if include_all or found == all:
                    lists[key].append(f"{list_key}: {found}/{all}")
            if not lists[key]:
                lists[key].append("No completion for this category :(")
        if not is_key_allowed("something"):
            del lists["Completion"]
    elif viewtype in ["maps", "maps_missing"]:
        missing = viewtype == "maps_missing"
        title = f"Clears {'missing' if missing else ''}"
        for key in valid_types:
            lists[key] = []
            for id in cache[key]["total"]:
                if not is_allowed(int(id)):
                    continue
                if (str(id) not in scores and missing) or (
                    str(id) in scores and not missing
                ):
                    beatmap = beatmaps.load_beatmap(id)
                    lists[key].append(
                        f"{id} | {beatmap['artist']} - {beatmap['title']} [{beatmap['difficulty_name']}]"
                    )
    view = StringListView(title, lists, size=15)
    await view.reply(message)


async def show_1s_leaderboard(full: str, split: list[str], message: discord.Message):
    cur = database.conn_lb.cursor()
    positions = cur.execute(
        "SELECT user_id FROM beatmaps_leaderboard WHERE position = 1"
    ).fetchall()
    cur.close()
    user_ids = {}
    for user_id in positions:
        user_id = user_id[0]
        if user_id in user_ids:
            user_ids[user_id] += 1
        else:
            user_ids[user_id] = 1
    user_ids = sorted(user_ids.items(), key=lambda x: x[1], reverse=True)[:10]
    str = "```"
    for user_id in user_ids:
        player = akatsuki.get_user_info(user_id[0])
        str += f"{player['name']}: {user_id[1]}\n"
    str += "```"
    await message.reply(content=str)


async def get_file(full: str, split: list[str], message: discord.Message):
    args = _parse_args(split)
    if len(args) == 0 or "default" not in args:
        await message.reply(f"Provide a file type!")
        return
    if args["default"] == "beatmaps":
        type = "akatsuki"
        if "type" in args:
            if (
                args["type"] != "akatsuki_ranked"
                and args["type"] != "akatsuki_loved"
                and args["type"] != "akatsuki"
            ):
                await message.reply(
                    f"Type needs to be akatsuki/akatsuki_ranked/akatsuki_loved!"
                )
                return
            type = args["type"]
        mode = 0
        if "mode" in args:
            if args["mode"] not in gamemodes:
                await _wrong_gamemode_warning(message)
                return
            mode = gamemodes[args["mode"]]["mode"]
        csv = ""
        cur = database.conn_uri.cursor()
        for field in cur.execute("PRAGMA table_info(beatmaps)").fetchall():
            csv += field[1] + ","
        csv = csv[:-1] + "\n"
        query = "SELECT * FROM beatmaps WHERE akatsuki_status BETWEEN 1 AND 4 AND bancho_status BETWEEN -2 AND 0 and mode = ?"
        if type == "akatsuki_loved":
            query = "SELECT * FROM beatmaps WHERE akatsuki_status = 4 AND bancho_status BETWEEN -2 AND 0 AND mode = ?"
        elif type == "akatsuki_ranked":
            query = "SELECT * FROM beatmaps WHERE akatsuki_status = 1 AND bancho_status BETWEEN -2 AND 0 AND mode = ?"
        for values in cur.execute(query, (mode,)):
            csv += ",".join([str(value) for value in values]) + "\n"
        await message.reply(
            file=discord.File(
                fp=io.BytesIO(bytes(csv, "utf-8")), filename="beatmaps.txt"
            )
        )
    elif args["default"] == "beatmapsets":
        type = "akatsuki"
        if "type" in args:
            if (
                args["type"] != "akatsuki_ranked"
                and args["type"] != "akatsuki_loved"
                and args["type"] != "akatsuki"
            ):
                await message.reply(
                    f"Type needs to be akatsuki/akatsuki_ranked/akatsuki_loved!"
                )
                return
            type = args["type"]
        mode = 0
        if "mode" in args:
            if args["mode"] not in gamemodes:
                await _wrong_gamemode_warning(message)
                return
            mode = gamemodes[args["mode"]]["mode"]
        csv = "beatmap_set_id,artist,title"
        cur = database.conn_uri.cursor()
        csv = csv[:-1] + "\n"
        query = "SELECT DISTINCT beatmap_set_id, title, artist FROM beatmaps WHERE akatsuki_status BETWEEN 1 AND 4 AND bancho_status BETWEEN -2 AND 0 and mode = ?"
        if type == "akatsuki_loved":
            query = "SELECT DISTINCT beatmap_set_id, title, artist FROM beatmaps WHERE akatsuki_status = 4 AND bancho_status BETWEEN -2 AND 0 AND mode = ?"
        elif type == "akatsuki_ranked":
            query = "SELECT DISTINCT beatmap_set_id, title, artist FROM beatmaps WHERE akatsuki_status = 1 AND bancho_status BETWEEN -2 AND 0 AND mode = ?"
        for values in cur.execute(query, (mode,)):
            csv += ",".join([str(value) for value in values]) + "\n"
        await message.reply(
            file=discord.File(
                fp=io.BytesIO(bytes(csv, "utf-8")), filename="beatmapsets.txt"
            )
        )
    else:
        await message.reply("Valid file types: beatmaps, beatmapsets")


async def search_maps(full: str, split: list[str], message: discord.Message):
    player, gamemode = await _get_linked_account(str(message.author.id))
    if not player:
        await _link_warning(message)
        return
    args = _parse_args(split, nodefault=True)
    date_pattern = "^\d{4}-\d{2}-\d{2}$"
    filters = list()
    unplayed = False
    view = "embed"

    def parse_value(value):
        if re.match(date_pattern, value):
            return int(datetime.datetime.strptime(value, "%Y/%m/%d").timestamp())
        return value

    for arg in args:
        if arg == "unplayed":
            unplayed = True
        elif arg == "view":
            view = args[arg]
        elif ":" in args[arg]:
            values = args[arg].split(":")
            filters.append(
                ("BETWEEN", (arg, parse_value(values[0]), parse_value(values[1])))
            )
        elif args[arg][0] in ["<", ">", "!"]:
            filters.append(
                ("COMPARISON", (arg, args[arg][0], parse_value(args[arg][1:])))
            )
        else:
            filters.append(("MATCH", (arg, args[arg])))
    query = ""
    for filter_type, filter_values in filters:
        filter = ""
        if filter_type == "MATCH":
            if filter_values[1].isnumeric():
                filter = f"{filter_values[0]} = {filter_values[1]}"
            else:
                filter = f"{filter_values[0]} LIKE '%{filter_values[1]}%'"
        elif filter_type == "BETWEEN":
            filter = (
                f"{filter_values[0]} BETWEEN {filter_values[1]} AND {filter_values[2]}"
            )
        elif filter_type == "COMPARISON":
            if filter_values[1] == "!":
                if filter_values[2].isnumeric():
                    filter = f"{filter_values[0]} != {filter_values[2]}"
                else:
                    filter = f"{filter_values[0]} NOT LIKE '%{filter_values[2]}%'"
            else:
                filter = f"{filter_values[0]} {filter_values[1]} {filter_values[2]}"
        if not filter:
            continue  # TODO
        if query:
            query += f" AND {filter}"
        else:
            query = f"SELECT * FROM beatmaps WHERE {filter}"
    if not query:
        if not unplayed:
            await message.reply(
                "usage: !searchmaps [field=to_match] [field=>X] [field=<X] [field=min:max] [field=YYYY-MM-DD] [unplayed=true]"
            )
            return
        query = "SELECT * FROM beatmaps"
    res = database.conn_uri.execute(query).fetchall()
    csv = (
        ",".join(
            [
                header[1]
                for header in database.conn_uri.execute(
                    "PRAGMA table_info('beatmaps')"
                ).fetchall()
            ]
        )
        + "\n"
    )
    blacklist = None
    if unplayed:
        blacklist = [
            x[0]
            for x in database.conn_uri.execute(
                "SELECT beatmap_id FROM users_scores WHERE user_id = ? AND mode = ?",
                (player["id"], gamemode),
            ).fetchall()
        ]
    if view == "embed":
        strs = list()
        count = 0

        for item in res:
            if blacklist and item[0] in blacklist:
                continue
            count += 1
            title = f"{item[3]}-{item[4]} {item[5]}"[:42]
            link = f"[{title}](https://kanaarima.github.io/osu/osudl.html?beatmap={item[0]})"
            strs.append(f"{item[21]:.2f}* | {item[13]/60:.2f} mins | {link}")
        view = StringListView(f"Search query results ({count})", {"result": strs})
        await view.reply(message)
        return
    elif view == "csv":
        count = 0
        for item in res:
            if blacklist and item[0] in blacklist:
                print(item[0])
                continue
            count += 1
            csv += ",".join(str(x) for x in item) + "\n"
        await message.reply(
            content=f"Found {count} beatmaps.",
            file=discord.File(
                fp=io.BytesIO(bytes(csv, "utf-8")), filename="beatmaps.csv"
            ),
        )
    else:
        await message.reply("Invalid view! Valid views: embed, csv")
        return


async def recommend(full: str, split: list[str], message: discord.Message):
    skip_id = []
    player, gamemode = await _get_linked_account(str(message.author.id))
    if not player:
        await _link_warning(message)
    _, stats = akatsuki.get_user_stats(player["id"], no_1s=True)
    top100 = akatsuki.get_user_best(player["id"], gamemodes["std_rx"])
    skip_id = [play["beatmap_id"] for play in top100[0]]
    total_pp = stats["std_rx"][0]["total_pp"]

    target = total_pp / 20
    min_pp = target - 20
    max_pp = target + 20

    mods_include = []
    mods_exclude = ["EZ", "FL"]
    algo = "old"
    matches_threshold = 0.85
    enable_apvn = False
    # Parse command arguments
    parsed = _parse_args(split, nodefault=True)

    if "magic" in parsed:
        enable_apvn = True
    if "min_pp" in parsed:
        if not parsed["min_pp"].isnumeric():
            await message.reply(content="pp value should be a number.")
            return
        min_pp = int(parsed["min_pp"])
        max_pp = min_pp + 20

    if "max_pp" in parsed:
        if not parsed["max_pp"].isnumeric():
            await message.reply(content="pp value should be a number.")
            return
        max_pp = int(parsed["max_pp"])

    if "threshold" in parsed:
        try:
            matches_threshold = float(parsed["threshold"])
        except:
            await message.reply(content="threshold value should be a number.")
            return

    if "include_mods" in parsed:
        mods_include = [
            parsed["include_mods"][i : i + 2]
            for i in range(0, len(parsed["include_mods"]), 2)
        ]
        for mod in mods_include:
            if mod in mods_exclude:
                mods_exclude.remove(mod)
    if "exclude_mods" in parsed:
        mods_exclude = [
            parsed["exclude_mods"][i : i + 2]
            for i in range(0, len(parsed["exclude_mods"]), 2)
        ]
    if "algo" in parsed:
        algo = parsed["algo"].lower().split(",")
        if algo == "auto":
            algo = [
                "aim",
                "stream",
            ]  # TODO: automatically chose algorithmn by top 100 plays
    mods = parsed["mods"].upper() if "mods" in parsed else None
    if mods:
        mods_exclude = []
        mods_include = []
    if algo == "old":
        recommend = farmer.recommend(
            pp_min=min_pp,
            pp_max=max_pp,
            mods=mods,
            mods_include=mods_include,
            mods_exclude=mods_exclude,
            skip_id=skip_id,
        )

        if not (beatmap := beatmaps.load_beatmap(recommend[0]["beatmap_id"])):
            await message.reply(content="Failed to load beatmap.")
            return
        title = f"{beatmap['title']} [{beatmap['difficulty_name']}] +{recommend[0]['mods']} {int(recommend[0]['average_pp'])}pp (confidence: {recommend[0]['weight']*100:.2f}%)"
    else:
        if enable_apvn:
            recommend = farmerv2.recommend_next(
                pp_min=min_pp,
                pp_max=max_pp,
                mods=mods_from_string(mods) if mods else None,
                mods_include=mods_include,
                mods_exclude=mods_exclude,
                servers=["bancho", "akatsuki"],
                skip_id=skip_id,
                models=algo,
            )
        else:
            recommend = farmer.recommend_next(
                pp_min=min_pp,
                pp_max=max_pp,
                mods=mods,
                mods_include=mods_include,
                mods_exclude=mods_exclude,
                skip_id=skip_id,
                matches_types=algo,
                matches_threshold=matches_threshold,
            )
        if not recommend:
            await message.reply(content="Nothing found.")
            return
        recommend = recommend[0]
        threshold = recommend["threshold"]
        algo = recommend["match"]
        mods = "".join(get_mods(recommend["future"]["mods"]))

        if not (beatmap := beatmaps.load_beatmap(recommend["future"]["beatmap_id"])):
            await message.reply(content="Failed to load beatmap.")
            return
        title = f"{beatmap['title']} [{beatmap['difficulty_name']}] +{mods} {int(recommend['pp_avg'])}pp (algo: {algo}, confidence: {threshold*100:.2f}%)"
    link = f"osu://b/{beatmap['beatmap_id']}"
    await message.reply(content=f"[{link} {title}]")


async def get_help(full: str, split: list[str], message: discord.Message):
    view = get_help_view()
    await view.reply(message)


async def _get_linked_account(discord_id: str) -> Tuple[Player, str]:
    c = database.ConnectionHandler()
    check = c.execute(
        "SELECT * FROM users WHERE discord_id = ?", (int(discord_id),)
    ).fetchall()
    c.close()
    if not check:
        return None, None
    return (
        Player(
            id=check[0][0], clan_id=check[0][1], name=check[0][2], country=check[0][3]
        ),
        check[0][5],
    )


async def _link_warning(message: discord.Message):
    await message.reply("You don't have an account linked! use !link username/userID.")


async def _wrong_gamemode_warning(message: discord.Message):
    await message.reply(f"Invalid gamemode! Valid gamemodes: {gamemodes.keys()}")


def _get_download_link(beatmap_id: int):
    return f"[direct](https://kanaarima.github.io/osu/osudl.html?beatmap={beatmap_id}) [bancho](https://osu.ppy.sh/b/{beatmap_id})"


def _update_fetch(player: Player, user_file: DataFile):
    user_file.load_data(default=[])
    for fetch in user_file.data:
        date = datetime.datetime.strptime(fetch[0], "%d/%m/%Y %H:%M:%S")
        if (datetime.datetime.now() - date) > datetime.timedelta(hours=24):
            user_file.data.remove(fetch)
    if not user_file.data:
        user_file.data.append(
            (
                datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                _add_extra(player, akatsuki.get_user_stats(player["id"])[1]),
            )
        )
    date = datetime.datetime.strptime(user_file.data[-1][0], "%d/%m/%Y %H:%M:%S")
    if (datetime.datetime.now() - date) > datetime.timedelta(minutes=5):
        user_file.data.append(
            (
                datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                _add_extra(player, akatsuki.get_user_stats(player["id"])[1]),
            )
        )


def _add_extra(player: Player, fetch):
    cur = database.ConnectionHandler()
    for name in gamemodes.keys():
        stats = fetch[name][0]
        if cur.execute(
            "SELECT * FROM users_scores WHERE user_id = ? LIMIT 1", (player["id"],)
        ).fetchall():
            stats["clears"] = cur.execute(
                "SELECT COUNT(score_id) FROM users_scores WHERE user_id = ? AND mode = ?",
                (player["id"], name),
            ).fetchall()[0][0]
        else:
            stats["clears"] = -1
        if "rx" not in name and "ap" not in name:
            continue
        if not cur.execute(
            "SELECT * FROM users_playtime WHERE user_id = ?", (player["id"],)
        ).fetchall():
            continue
        submitted_plays, unsubmitted_plays, most_played = cur.execute(
            "SELECT submitted_plays, unsubmitted_plays, most_played FROM users_playtime WHERE user_id = ? AND mode = ?",
            (player["id"], name),
        ).fetchall()[0]
        stats["play_time"] = submitted_plays + unsubmitted_plays + most_played
    cur.close()
    return fetch


def _format_gain_string(gain, fix=""):
    is_float = type(gain) == float
    if gain == 0:
        return ""
    if gain > 0:
        return f"(+{gain:,.2f}{fix})" if is_float else f"(+{gain:,}{fix})"
    else:
        return f"({gain:,.2f}{fix})" if is_float else f"({gain:,}{fix})"


def _format_notation(gain):
    return "" if gain == 0 else f"(+{gain:.2e})"


def _parse_args(args: List[str], nodefault=False) -> dict:
    parsed = {}
    for arg in args:
        s = arg.split("=")
        if len(s) == 1:
            if "default" in parsed or nodefault:
                parsed[arg] = ""
            else:
                parsed["default"] = arg
        else:
            parsed[s[0]] = s[1]
    return parsed
