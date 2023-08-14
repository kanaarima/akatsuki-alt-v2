from enum import Enum
from api.objects import Gamemode, Player, GamemodeStatistics, Score
import utils.api

requests = utils.api.ApiHandler(base_url="https://akatsuki.gg/api/v1/")


class Sort_Method(Enum):
    PP = "pp"
    SCORE = "score"
    PP_ALL = "magic"


def get_user_leaderboard(gamemode: Gamemode, sort: Sort_Method, pages=1, length=100):
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
            stats = GamemodeStatistics(
                ranked_score=apiuser["chosen_mode"]["ranked_score"],
                total_score=apiuser["chosen_mode"]["total_score"],
                play_count=apiuser["chosen_mode"]["playcount"],
                play_time=apiuser["chosen_mode"]["playtime"],
                accuracy=apiuser["chosen_mode"]["accuracy"],
                total_hits=apiuser["chosen_mode"]["total_hits"],
                total_pp=apiuser["chosen_mode"]["pp"],
            )
            res.append((user, stats))
    return res


def get_user_1s(userid: int, gamemode: Gamemode, pages=1, length=100):
    res = list()
    for page in range(pages):
        req = requests.get_request(
            f"users/scores/first?mode={gamemode['mode']}&rx={gamemode['relax']}&p={page+1}&l={length}&id={userid}"
        )
        if req.status_code != 200:  # TODO:
            return res
        apiscores = req.json()["scores"]
        if not apiscores:
            return res
        for apiscore in apiscores:
            res.append(
                Score(
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
            )
    return res
