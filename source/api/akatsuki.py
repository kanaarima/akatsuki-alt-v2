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
import api.beatmaps as beatmaps
import api.objects as objects
from enum import Enum
import utils.api
import datetime

requests = utils.api.ApiHandler(base_url="https://akatsuki.gg/api/v1/", delay=0.8)
lb_score_cache: Dict[str, List[Tuple[Player, GamemodeStatistics, Ranking]]] = {}
lb_total_score_cache: Dict[str, List[Tuple[Player, GamemodeStatistics, Ranking]]] = {}
last_fetched = datetime.datetime(year=1984, month=1, day=1)


class Sort_Method(Enum):
    PP = "pp"
    SCORE = "score"
    PP_ALL = "magic"
    COUNT_1S = "1s"


def _stats_from_chosen_mode(chosen_mode) -> GamemodeStatistics:
    return GamemodeStatistics(
        ranked_score=chosen_mode["ranked_score"],
        total_score=chosen_mode["total_score"],
        play_count=chosen_mode["playcount"],
        play_time=chosen_mode["playtime"],
        profile_accuracy=chosen_mode["accuracy"],
        total_hits=chosen_mode["total_hits"],
        watched_replays=chosen_mode["replays_watched"],
        level=chosen_mode["level"],
        total_pp=chosen_mode["pp"],
        max_combo=chosen_mode["max_combo"],
    )


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
        completed=apiscore["completed"],
        date=datetime.datetime.fromisoformat(
            apiscore["time"][:-1] + "+00:00"
        ).timestamp(),
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
        difficulty_name=difficulty,
    )


def search_users(username: str) -> List[Player]:
    res = []
    req = requests.get_request(f"users/lookup?name={username}")
    apiusers = req.json()["users"]
    if not apiusers:
        return res
    res.extend(
        Player(name=apiuser["username"], id=apiuser["id"]) for apiuser in apiusers
    )
    return res


def lookup_user(username: str) -> int:
    req = requests.get_request(f"users/whatid?name={username}")
    return None if req.status_code != 200 else req.json()["id"]


def get_user_leaderboard(
    gamemode: Gamemode, sort: Sort_Method, pages=1, length=100
) -> List[Tuple[Player, GamemodeStatistics, Ranking]]:
    res = []
    rank = 0
    country_rank = {}

    def get(country):
        if country in country_rank:
            country_rank[country] += 1
            return country_rank[country]
        else:
            country_rank[country] = 1
            return 1

    for page in range(pages):
        req = requests.get_request(
            f"leaderboard?mode={gamemode['mode']}&p={page+1}&l={length}&rx={gamemode['relax']}&sort={sort.value}"
        )
        if req.status_code != 200:
            break
        apiusers = req.json()["users"]
        if not apiusers:
            break

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
            if sort != Sort_Method.PP:
                ranking = Ranking(
                    global_ranking=rank, country_ranking=get(user["country"])
                )
            if not ranking["global_ranking"]:  # rare case, not sure why it happens
                ranking = Ranking(global_ranking=-1, country_ranking=-1)

            res.append((user, stats, ranking))
    return res


def get_user_1s(
    userid: int, gamemode: Gamemode, pages=1, length=100
) -> Tuple[int, List[Score], List[Beatmap]]:
    res = []
    resmaps = []
    total = 0
    for page in range(pages):
        req = requests.get_request(
            f"users/scores/first?mode={gamemode['mode']}&rx={gamemode['relax']}&p={page+1}&l={length}&id={userid}"
        )
        if req.status_code != 200:
            break
        apiscores = req.json()["scores"]
        total = req.json()["total"]
        if not apiscores:
            break
        for apiscore in apiscores:
            res.append(_score_from_apiscore(apiscore, gamemode))
            resmaps.append(_beatmap_from_apimap(apiscore["beatmap"]))
    return total, res, resmaps


def get_user_recent(
    userid: int, gamemode: Gamemode, skip=0, pages=1, length=1
) -> Tuple[List[Score], List[Beatmap]]:
    res = []
    resmaps = []
    for page in range(pages):
        req = requests.get_request(
            f"users/scores/recent?mode={gamemode['mode']}&rx={gamemode['relax']}&p={page+1+skip}&l={length}&id={userid}"
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


def get_user_best(
    userid: int, gamemode: Gamemode, pages=1, length=100
) -> Tuple[List[Score], List[Beatmap]]:
    res = []
    resmaps = []
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


def get_user_most_played(
    userid: int, gamemode: Gamemode, pages=1, length=100
) -> List[Tuple[int, Beatmap]]:
    res = []
    for page in range(pages):
        req = requests.get_request(
            f"users/most_played?mode={gamemode['mode']}&rx={gamemode['relax']}&p={page+1}&l={length}&id={userid}"
        )
        if req.status_code != 200:
            break
        if most_played := req.json()["most_played_beatmaps"]:
            res.extend(
                (object["playcount"], _beatmap_from_apimap(object["beatmap"]))
                for object in most_played
            )
        else:
            break
    return res


def get_user_stats(
    userid: int,
    no_1s=False,
) -> Tuple[Player, Dict[str, Tuple[GamemodeStatistics, Ranking, Ranking]]]:
    req = requests.get_request(f"users/full?id={userid}&relax=-1")
    if req.status_code != 200:
        return
    update_score_cache()
    data = req.json()
    user = Player(id=data["id"], name=data["username"], country=data["country"])
    if data["clan"]:
        user["clan_id"] = data["clan"]["id"]
    user_stats = {}
    for name, gamemode in objects.gamemodes.items():
        apistats = data["stats"][gamemode["relax"]][name.split("_")[0]]
        stats = _stats_from_chosen_mode(apistats)
        if not no_1s:
            stats["total_1s"] = get_user_1s(userid=userid, gamemode=gamemode, length=1)[
                0
            ]
        ranking_pp = Ranking(
            global_ranking=apistats["global_leaderboard_rank"],
            country_ranking=apistats["country_leaderboard_rank"],
        )
        if not ranking_pp["global_ranking"]:
            ranking_pp = Ranking(global_ranking=-1, country_ranking=-1)
        ranking_score = Ranking(global_ranking=-1, country_ranking=-1)
        ranking_total_score = Ranking(global_ranking=-1, country_ranking=-1)
        for player, _, ranking in lb_score_cache[name]:
            if player["id"] == user["id"]:
                ranking_score = ranking
                break
        for player, _, ranking in lb_total_score_cache[name]:
            if player["id"] == user["id"]:
                ranking_total_score = ranking
                break
        stats["total_score_rank"] = ranking_total_score
        user_stats[name] = (stats, ranking_score, ranking_pp)
    return (user, user_stats)


def get_user_info(userid: int) -> Player:
    req = requests.get_request(f"users?id={userid}")
    if req.status_code != 200:
        return None
    data = req.json()
    return Player(
        name=data["username"],
        country=data["country"],
        id=data["id"],
    )


def get_clan_leaderboard(
    gamemode: Gamemode, sort: Sort_Method, pages=1, length=50
) -> List[Tuple[Clan, GamemodeStatistics, Ranking]]:
    res = []
    rank = 1
    for page in range(pages):
        if sort == Sort_Method.COUNT_1S:
            req = requests.get_request(
                f"clans/stats/first?m={gamemode['mode']}&rx={gamemode['relax']}&p={page+1}&l={length}"
            )
            if req.status_code != 200:
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
            if req.status_code != 200:
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


def get_map_leaderboard(
    beatmap_id, gamemode: Gamemode, pages=1
) -> List[Tuple[Player, Score]]:
    beatmap = beatmaps.load_beatmap(beatmap_id)
    if not beatmap:
        return
    if "attributes" not in beatmap:
        return
    if gamemode["mode"] != beatmap["attributes"]["mode"]:
        if beatmap["attributes"]["mode"] != 0:  # Allow converts
            return
    res = []
    for page in range(pages):
        req = requests.get_request(
            f"scores?b={beatmap_id}&l=100&p={page+1}&relax={gamemode['relax']}"
        )
        if req.status_code != 200:
            break
        scores = req.json()["scores"]
        if not scores:
            break
        for score in scores:
            player = Player(
                id=score["user"]["id"],
                name=score["user"]["username"],
                country=score["user"]["country"],
            )
            score["beatmap"] = {"beatmap_id": beatmap_id}
            res.append((player, _score_from_apiscore(score, gamemode)))
    return res


def get_map_info(beatmap_id: int):
    res = requests.get_request(f"beatmaps?b={beatmap_id}")
    if res.status_code != 200:
        return
    return res.json()


def update_score_cache():
    global last_fetched, lb_score_cache, lb_total_score_cache
    fetch = False
    if (datetime.datetime.now() - last_fetched) > datetime.timedelta(minutes=30):
        fetch = True
    if not fetch:
        return
    last_fetched = datetime.datetime.now()
    for name, gamemode in objects.gamemodes.items():
        pages = 8 if gamemode["mode"] == 0 and gamemode["relax"] == 1 else 1
        lb_score_cache[name] = get_user_leaderboard(
            gamemode=gamemode, sort=Sort_Method.SCORE, pages=pages
        )
    lb_total_score_cache = {}

    for name, gamemode in objects.gamemodes.items():
        rank = 0
        country_rank = {}
        lb_total_score_cache[name] = []
        total_score_lb = sorted(
            lb_score_cache[name], key=lambda x: x[1]["total_score"], reverse=True
        )

        def get(country):
            if country in country_rank:
                country_rank[country] += 1
                return country_rank[country]
            else:
                country_rank[country] = 1
                return 1

        for player, stats, _ in total_score_lb:
            rank += 1
            lb_total_score_cache[name].append(
                (
                    player,
                    stats,
                    Ranking(
                        global_ranking=rank, country_ranking=get(player["country"])
                    ),
                )
            )
