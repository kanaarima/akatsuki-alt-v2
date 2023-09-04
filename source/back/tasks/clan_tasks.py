from api.tasks import Task, TaskStatus
from api.utils import update_dicts, yesterday
from api.files import DataFile, exists
from api import objects, akatsuki
from config import config


class StoreClanLeaderboardsTask(Task):
    def __init__(self) -> None:
        super().__init__()

    def can_run(self) -> bool:
        return not exists(self._get_path())

    def run(self) -> TaskStatus:
        data = {}
        for name, gamemode in objects.gamemodes.items():
            data[name] = []
            leaderboard_1s = akatsuki.get_clan_leaderboard(
                gamemode=gamemode, sort=akatsuki.Sort_Method.COUNT_1S, pages=2
            )
            leaderboard_pp = akatsuki.get_clan_leaderboard(
                gamemode=gamemode, sort=akatsuki.Sort_Method.PP, pages=4
            )
            # Find clans who are in both leaderboards
            for clan_a, stats_a, ranking_1s in leaderboard_1s:
                for clan_b, stats_b, ranking_pp in leaderboard_pp:
                    if clan_a["clan_id"] == clan_b["clan_id"]:
                        update_dicts(stats_a, stats_b)
                        data[name].append((clan_a, stats_a, ranking_1s, ranking_pp))
                        break
            # Find clans who are only in #1 leaderboard
            for clan_a, stats_a, ranking_1s in leaderboard_1s:
                for clan_b, stats_b, ranking_pp in leaderboard_pp:
                    if clan_a["clan_id"] == clan_b["clan_id"]:
                        break
                else:  # clan isn't on both leaderboards
                    data[name].append(
                        (
                            clan_a,
                            stats_a,
                            ranking_1s,
                            objects.Ranking(global_ranking=-1),
                        )
                    )
            # Find clans who are only in pp leaderboard
            for clan_a, stats_a, ranking_1s in leaderboard_pp:
                for clan_b, stats_b, ranking_pp in leaderboard_1s:
                    if clan_a["clan_id"] == clan_b["clan_id"]:
                        break
                else:  # clan isn't on both leaderboards
                    data[name].append(
                        (
                            clan_a,
                            stats_a,
                            objects.Ranking(global_ranking=-1),
                            ranking_pp,
                        )
                    )
        file = DataFile(filepath=self._get_path())
        file.data = data
        file.save_data()
        return self._finish()

    def _get_path(self) -> str:
        return f"{config['common']['data_directory']}/leaderboards/clans/{yesterday()}.json.gz"
