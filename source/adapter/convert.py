from api.files import DataFile
import adapter.types as types
import api.objects as objects
import glob


def convert_old_clan(oldclan: types.old_clan, data: dict = None):
    if data is None:
        data = {}
    for gamemode in objects.gamemodes.keys():
        if gamemode not in data:
            data[gamemode] = list()
    clan = objects.Clan(
        clan_id=oldclan["id"], clan_name=oldclan["name"], clan_tag=oldclan["tag"]
    )
    for gamemode in objects.gamemodes.keys():
        if types.new_gamemodes_to_old[gamemode] not in oldclan["statistics"]:
            continue
        old_stats: types.old_stats = oldclan["statistics"][
            types.new_gamemodes_to_old[gamemode]
        ]
        stats = objects.GamemodeStatistics()
        fp_rank = objects.Ranking(global_ranking=-1)
        pp_rank = objects.Ranking(global_ranking=-1)

        if oldclan["tag"]:
            fp_rank = objects.Ranking(global_ranking=old_stats["1s_rank"])
            stats["total_1s"] = old_stats["first_places"]
        if old_stats["performance_points"]:
            pp_rank = objects.Ranking(global_ranking=old_stats["pp_rank"])
            stats["play_count"] = old_stats["play_count"]
            stats["ranked_score"] = old_stats["ranked_score"]
            stats["total_score"] = old_stats["total_score"]
            stats["profile_accuracy"] = old_stats["accuracy"]
            stats["total_pp"] = old_stats["performance_points"]
        data[gamemode].append((clan, stats, fp_rank, pp_rank))
    return data


def convert_old_user(user):
    player = objects.Player(
        id=user["id"], name=user["username"], country=user["country"]
    )
    first_places = dict()
    statistics = dict()
    for name, gamemode in objects.gamemodes.items():
        first_places[name] = list()
        old_stats = user["stats"][gamemode["relax"]][name.split("_")[0]]
        score_rank = objects.Ranking(
            global_ranking=old_stats["global_rank_score"],
            country_ranking=old_stats["country_rank_score"],
        )
        pp_rank = objects.Ranking(
            global_ranking=old_stats["global_leaderboard_rank"],
            country_ranking=old_stats["country_leaderboard_rank"],
        )
        stats = objects.GamemodeStatistics()
        stats["ranked_score"] = old_stats["ranked_score"]
        stats["total_score"] = old_stats["total_score"]
        stats["total_hits"] = old_stats["total_hits"]
        stats["level"] = old_stats["level"]
        stats["profile_accuracy"] = old_stats["accuracy"]
        stats["max_combo"] = old_stats["max_combo"]
        stats["total_1s"] = old_stats["count_1s"]
        stats["total_pp"] = old_stats["pp"]
        stats["watched_replays"] = old_stats["replays_watched"]
        stats["play_count"] = old_stats["playcount"]
        stats["play_time"] = old_stats["playtime"]
        if "first_places" in user:
            for apiscore in user["first_places"][gamemode["mode"]][gamemode["relax"]]:
                first_places[name].append(_score_from_apiscore(apiscore, gamemode))
        statistics[name] = (stats, score_rank, pp_rank)
    return {"player": player, "statistics": statistics, "first_places": first_places}


def run(kind, source, target):
    if kind == "clan":
        files = glob.glob(f"{source}/*.json.gz")
    else:
        files = glob.glob(f"{source}/*/*.json.gz")
    for file in files:
        filedata = DataFile(file)
        filedata.load_data()
        targetdata = DataFile(f"{target}/{file.replace(source, '')}")
        targetdata.load_data()
        targetdata.data = {"notempty": ""}
        if kind == "clan":
            for oldclan in filedata.data:
                convert_old_clan(oldclan, targetdata.data)
        elif kind == "user":
            targetdata.data = convert_old_user(filedata.data)
        targetdata.save_data()


def _score_from_apiscore(apiscore, gamemode):
    return objects.Score(
        id=int(apiscore["id"]),
        beatmap_id=apiscore["beatmap"],
        mode=gamemode["mode"],
        mods=apiscore["mods"],
        accuracy=apiscore["accuracy"],
        count_300=apiscore["count_300"],
        count_100=apiscore["count_100"],
        count_50=apiscore["count_50"],
        count_miss=apiscore["count_miss"],
        pp=apiscore["pp"],
        combo=apiscore["max_combo"],
        score=apiscore["score"],
        rank=apiscore["rank"],
        completed=apiscore["completed"],
    )
