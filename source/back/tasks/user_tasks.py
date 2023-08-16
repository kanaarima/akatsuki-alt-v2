from api.tasks import Task, TaskStatus
from api.utils import update_dicts, yesterday, find_unique
from api.files import DataFile, exists
from api import objects, akatsuki
from config import config


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