from api.tasks import Task, TaskStatus
from api.utils import update_dicts, yesterday, find_unique
from api.files import DataFile, exists
from api import objects, akatsuki
from config import config
from typing import List


class StoreUserLeaderboardsTask(Task):
    def __init__(self) -> None:
        super().__init__()

    def can_run(self) -> bool:
        return not exists(self._get_path())

    def run(self) -> TaskStatus:
        data = {}
        for name, gamemode in objects.gamemodes.items():
            data[name] = list()
            leaderboard_pp = akatsuki.get_user_leaderboard(
                gamemode=gamemode, sort=akatsuki.Sort_Method.PP, pages=10
            )
            leaderboard_score = akatsuki.get_user_leaderboard(
                gamemode=gamemode, sort=akatsuki.Sort_Method.SCORE, pages=5
            )
            for player_a, stats_a, ranking_pp in leaderboard_pp:
                for player_b, stats_b, ranking_score in leaderboard_score:
                    if player_a["id"] == player_b["id"]:
                        data[name].append(
                            (player_a, stats_a, ranking_score, ranking_pp)
                        )
                        break

            def same(tupleA, tupleB):
                return tupleA[0]["id"] == tupleB[0]["id"]

            only_pp, only_score = find_unique(same, leaderboard_pp, leaderboard_score)
            for player, stats, ranking_pp in only_pp:
                data[name].append(
                    (
                        player,
                        stats,
                        objects.Ranking(global_ranking=-1, country_ranking=-1),
                        ranking_pp,
                    )
                )
            for player, stats, ranking_score in only_score:
                data[name].append(
                    (
                        player,
                        stats,
                        ranking_score,
                        objects.Ranking(global_ranking=-1, country_ranking=-1),
                    )
                )
        file = DataFile(filepath=self._get_path())
        file.data = data
        file.save_data()
        return self._finish()

    def _get_path(self) -> str:
        return f"{config['common']['data_directory']}/leaderboards/users/{yesterday()}.json.gz"


class StorePlayerStats(Task):
    def __init__(self) -> None:
        super().__init__(asynchronous=False)

    def can_run(self) -> bool:
        return not exists(self._get_path()) and exists(self._get_path_users())

    def run(self) -> TaskStatus:
        usersfile = DataFile(filepath=self._get_path_users())
        usersfile.load_data(default=list())
        users: List[objects.LinkedPlayer] = usersfile.data
        for user in users:
            if not user["full_tracking"]:
                continue
            userfile = DataFile(
                filepath=self._get_path() + f"{user['user_id']}.json.gz"
            )
            userfile.data = {}
            player, stats = akatsuki.get_user_stats(user["user_id"])
            first_places = dict()
            for name, gamemode in objects.gamemodes.items():
                _, first_places[name], beatmaps = akatsuki.get_user_1s(
                    userid=user["user_id"],
                    gamemode=gamemode,
                    pages=1000,
                )
            userfile.data["player"] = player
            userfile.data["statistics"] = stats
            userfile.data["first_places"] = first_places
            userfile.save_data()
        return self._finish()

    def _get_path(self) -> str:
        return f"{config['common']['data_directory']}/users_statistics/{yesterday()}/"

    def _get_path_users(self) -> str:
        return f"{config['common']['data_directory']}/users_statistics/users.json.gz"
