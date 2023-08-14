from enum import Enum
from api.objects import Gamemode, Player, GamemodeStatistics
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
        for apiuser in req.json()["users"]:
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
