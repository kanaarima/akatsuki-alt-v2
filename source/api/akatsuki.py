from api.objects import Gamemode, Player, GamemodeStatistics, Score, Clan, Ranking
from typing import List, Tuple, Dict
from enum import Enum
import api.objects as objects
import utils.api

requests = utils.api.ApiHandler(base_url="https://akatsuki.gg/api/v1/")


class Sort_Method(Enum):
    PP = "pp"
    SCORE = "score"
    PP_ALL = "magic"
    COUNT_1S = "1s"


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


def get_user_leaderboard(
    gamemode: Gamemode, sort: Sort_Method, pages=1, length=100
) -> List[Tuple[Player, GamemodeStatistics, Ranking]]:
    res = list()
    for page in range(pages):
        req = requests.get_request(
            f"leaderboard?mode={gamemode['mode']}&p={page+1}&l={length}&rx={gamemode['relax']}&sort={sort}"
        )
        if req.status_code != 200:  # TODO:
            return res
        apiusers = req.json()["users"]
        if not apiusers:
            return res
        for apiuser in apiusers:
            user = Player(
                id=apiuser["id"], name=apiuser["username"], country=apiuser["country"]
            )
            stats = _stats_from_chosen_mode(apiuser["chosen_mode"])
            ranking = Ranking(
                global_ranking=apiuser["chosen_mode"]["global_leaderboard_rank"],
                country_ranking=apiuser["chosen_mode"]["country_leaderboard_rank"],
            )
            res.append((user, stats, ranking))
    return res


def get_user_1s(
    userid: int, gamemode: Gamemode, pages=1, length=100
) -> Tuple[int, List[Score]]:
    res = list()
    total = 0
    for page in range(pages):
        req = requests.get_request(
            f"users/scores/first?mode={gamemode['mode']}&rx={gamemode['relax']}&p={page+1}&l={length}&id={userid}"
        )
        if req.status_code != 200:  # TODO:
            return total, res
        apiscores = req.json()["scores"]
        total = apiscores["total"]
        if not apiscores:
            return total, res
        for apiscore in apiscores:
            res.append(_score_from_apiscore(apiscore))
    return total, res


def get_user_best(userid: int, gamemode: Gamemode, pages=1, length=100) -> List[Score]:
    res = list()
    for page in range(pages):
        req = requests.get_request(
            f"users/scores/best?mode={gamemode['mode']}&rx={gamemode['relax']}&p={page+1}&l={length}&id={userid}"
        )
        if req.status_code != 200:
            return res
        apiscores = req.json()["scores"]
        if not apiscores:
            return res
        for apiscore in apiscores:
            res.append(_score_from_apiscore(apiscore, gamemode))
    return res


def get_user_stats(
    userid: int,
) -> Tuple[Player, Dict[str, Tuple[GamemodeStatistics, Ranking]]]:
    req = requests.get_request(f"users/full?id={userid}&relax=-1")
    if req.status_code != 200:
        return
    data = req.json()
    user = Player(id=data["id"], name=data["username"], country=data["country"])
    user_stats = dict()
    for name, gamemode in objects.gamemodes.items():
        apistats = data["stats"][gamemode["relax"]][name.split("_")[0]]
        stats = _stats_from_chosen_mode(apistats)
        ranking = Ranking(
            global_ranking=apistats["global_leaderboard_rank"],
            country_ranking=apistats["country_leaderboard_rank"],
        )
        user_stats[name] = (stats, ranking)
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
                return res
            apiclans = req.json()["clans"]
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
                return res
            apiclans = req.json()["clans"]
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
