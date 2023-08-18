from api.objects import (
    Gamemode,
    Player,
    GamemodeStatistics,
    Score,
    Clan,
    Ranking,
    Beatmap,
)
from typing import List, Tuple, Dict
from enum import Enum
import api.objects as objects
import datetime
import utils.api

requests = utils.api.ApiHandler(base_url="https://akatsuki.gg/api/v1/")
lb_score_cache: Dict[str, List[Tuple[Player, GamemodeStatistics, Ranking]]] = dict()
last_fetched = None


class Sort_Method(Enum):
    PP = "pp"
    SCORE = "score"
    PP_ALL = "magic"
    COUNT_1S = "1s"


Sort_Method.PP


def _stats_from_chosen_mode(chosen_mode) -> GamemodeStatistics:
    stats = GamemodeStatistics(
        ranked_score=chosen_mode["ranked_score"],
        total_score=chosen_mode["total_score"],
        play_count=chosen_mode["playcount"],
        play_time=chosen_mode["playtime"],
        accuracy=chosen_mode["accuracy"],
        total_hits=chosen_mode["total_hits"],
        total_pp=chosen_mode["pp"],
    )
    return stats


def _score_from_apiscore(apiscore, gamemode: Gamemode) -> Score:
    return Score(
        id=int(apiscore["id"]),
        beatmap_id=apiscore["beatmap"]["beatmap_id"],
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
    )


def _beatmap_from_apimap(apimap):
    s = apimap["song_name"].split("-")
    s2 = apimap["song_name"].split("[")
    artist = s[0]
    title = s[1].split("[")[0]
    difficulty = s2[1][:-1]
    return Beatmap(
        beatmap_id=apimap["beatmap_id"],
        beatmap_set_id=apimap["beatmapset_id"],
        artist=artist,
        title=title,
        difficulty=difficulty,
        star_rating=apimap["difficulty"],
        length=apimap["hit_length"],
        drain_time=apimap["hit_length"],
        max_combo=apimap["max_combo"],
        ar=apimap["ar"],
        od=apimap["od"],
    )


def get_user_leaderboard(
    gamemode: Gamemode, sort: Sort_Method, pages=1, length=100
) -> List[Tuple[Player, GamemodeStatistics, Ranking]]:
    res = list()
    for page in range(pages):
        req = requests.get_request(
            f"leaderboard?mode={gamemode['mode']}&p={page+1}&l={length}&rx={gamemode['relax']}&sort={sort.value}"
        )
        if req.status_code != 200:  # TODO:
            break
        apiusers = req.json()["users"]
        if not apiusers:
            break
        rank = 0
        country_rank = {}

        def get(country):
            if country in country_rank:
                country_rank[country] += 1
                return country_rank[country]
            else:
                country_rank[country] = 1
                return 1

        for apiuser in apiusers:
            rank += 1
            user = Player(
                id=apiuser["id"], name=apiuser["username"], country=apiuser["country"]
            )
            stats = _stats_from_chosen_mode(apiuser["chosen_mode"])
            ranking = Ranking(
                global_ranking=apiuser["chosen_mode"]["global_leaderboard_rank"],
                country_ranking=apiuser["chosen_mode"]["country_leaderboard_rank"],
            )
            if sort != Sort_Method.PP or not ranking["global_ranking"]:
                ranking = Ranking(
                    global_ranking=rank, country_ranking=get(user["country"])
                )
            res.append((user, stats, ranking))
    return res


def get_user_1s(
    userid: int, gamemode: Gamemode, pages=1, length=100
) -> Tuple[int, List[Score], List[Beatmap]]:
    res = list()
    resmaps = list()
    total = 0
    for page in range(pages):
        req = requests.get_request(
            f"users/scores/first?mode={gamemode['mode']}&rx={gamemode['relax']}&p={page+1}&l={length}&id={userid}"
        )
        if req.status_code != 200:  # TODO:
            break
        apiscores = req.json()["scores"]
        total = req.json()["total"]
        if not apiscores:
            break
        for apiscore in apiscores:
            res.append(_score_from_apiscore(apiscore, gamemode))
            resmaps.append(_beatmap_from_apimap(apiscore["beatmap"]))
    return total, res, resmaps


def get_user_best(
    userid: int, gamemode: Gamemode, pages=1, length=100
) -> Tuple[List[Score], List[Beatmap]]:
    res = list()
    resmaps = list()
    for page in range(pages):
        req = requests.get_request(
            f"users/scores/best?mode={gamemode['mode']}&rx={gamemode['relax']}&p={page+1}&l={length}&id={userid}"
        )
        if req.status_code != 200:
            break
        apiscores = req.json()["scores"]
        if not apiscores:
            break
        for apiscore in apiscores:
            res.append(_score_from_apiscore(apiscore, gamemode))
            resmaps.append(_beatmap_from_apimap(apiscore["beatmap"]))
    return res, resmaps


def get_user_stats(
    userid: int,
) -> Tuple[Player, Dict[str, Tuple[GamemodeStatistics, Ranking, Ranking]]]:
    req = requests.get_request(f"users/full?id={userid}&relax=-1")
    if req.status_code != 200:
        return
    update_score_cache()
    data = req.json()
    user = Player(id=data["id"], name=data["username"], country=data["country"])
    user_stats = dict()
    for name, gamemode in objects.gamemodes.items():
        apistats = data["stats"][gamemode["relax"]][name.split("_")[0]]
        stats = _stats_from_chosen_mode(apistats)
        stats["total_1s"] = get_user_1s(userid=userid, gamemode=gamemode, length=1)[0]
        ranking_pp = Ranking(
            global_ranking=apistats["global_leaderboard_rank"],
            country_ranking=apistats["country_leaderboard_rank"],
        )
        if not ranking_pp["global_ranking"]:
            ranking_pp = Ranking(global_ranking=-1, country_ranking=-1)
        ranking_score = Ranking(global_ranking=-1, country_ranking=-1)
        for player, stats, ranking in lb_score_cache[name]:
            if player["id"] == user["id"]:
                ranking_score = ranking
                break
        user_stats[name] = (stats, ranking_score, ranking_pp)
    return (user, user_stats)


def get_clan_leaderboard(
    gamemode: Gamemode, sort: Sort_Method, pages=1, length=50
) -> List[Tuple[Clan, GamemodeStatistics, Ranking]]:
    res = list()
    rank = 1
    for page in range(pages):
        if sort == Sort_Method.COUNT_1S:
            req = requests.get_request(
                f"clans/stats/first?m={gamemode['mode']}&rx={gamemode['relax']}&p={page+1}&l={length}"
            )
            if req.status_code != 200:  # TODO:
                break
            apiclans = req.json()["clans"]
            if not apiclans:
                break
            for apiclan in apiclans:
                clan = Clan(
                    clan_id=apiclan["clan"],
                    clan_name=apiclan["name"],
                    clan_tag=apiclan["tag"],
                )
                stats = GamemodeStatistics(total_1s=apiclan["count"])
                ranking = Ranking(
                    global_ranking=rank,
                )
                res.append((clan, stats, ranking))
                rank += 1
        else:
            req = requests.get_request(
                f"clans/stats/all?m={gamemode['mode']}&rx={gamemode['relax']}&p={page+1}&l={length}"
            )
            if req.status_code != 200:  # TODO:
                break
            apiclans = req.json()["clans"]
            if not apiclans:
                break
            for apiclan in apiclans:
                clan = Clan(
                    clan_id=apiclan["id"],
                    clan_name=apiclan["name"],
                )
                stats = _stats_from_chosen_mode(apiclan["chosen_mode"])
                ranking = Ranking(
                    global_ranking=rank,
                )
                res.append((clan, stats, ranking))
                rank += 1
    return res


def get_clan_stats(
    clan_id, gamemode: Gamemode
) -> Tuple[Clan, GamemodeStatistics, Ranking]:
    req = requests.get_request(
        f"clans/stats?id={clan_id}&m={gamemode['mode']}&rx={gamemode['relax']}"
    )
    if req.status_code != 200:
        return
    data = req.json()
    clan = Clan(
        clan_id=data["clan"]["id"],
        clan_name=data["clan"]["name"],
        clan_tag=data["clan"]["tag"],
    )
    stats = _stats_from_chosen_mode(data["clan"]["chosen_mode"])
    ranking = Ranking(
        global_ranking=data["clan"]["chosen_mode"]["global_leaderboard_rank"]
    )
    return (clan, stats, ranking)


def update_score_cache():
    fetch = not last_fetched
    if (datetime.datetime.now() - last_fetched) > datetime.timedelta(minutes=30):
        fetch = True
    if not fetch:
        return
    last_fetched = datetime.datetime.now()
    for name, gamemode in objects.gamemodes.items():
        pages = 2 if gamemode["mode"] == 0 else 1
        lb_score_cache[name] = get_user_leaderboard(
            gamemode=gamemode, sort=Sort_Method.SCORE, pages=pages
        )


update_score_cache()
