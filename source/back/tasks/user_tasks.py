from api.utils import (
    yesterday,
    find_unique,
    datetime_to_str,
    str_to_datetime,
)
from api.tasks import Task, TaskStatus
from api.files import DataFile, exists
from api.beatmaps import save_beatmaps, load_beatmap
from api import objects, akatsuki
from config import config
from typing import List
import datetime


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
                save_beatmaps(beatmaps)
            userfile.data["player"] = player
            userfile.data["statistics"] = stats
            userfile.data["first_places"] = first_places
            userfile.save_data()
        return self._finish()

    def _get_path(self) -> str:
        return f"{config['common']['data_directory']}/users_statistics/{yesterday()}/"

    def _get_path_users(self) -> str:
        return f"{config['common']['data_directory']}/users_statistics/users.json.gz"


class StorePlayerScores(Task):
    def __init__(self) -> None:
        super().__init__(asynchronous=False)

    def can_run(self) -> bool:
        userfile = DataFile(self._get_path_users())
        userfile.load_data(default=list())
        infofile = DataFile(f"{self._get_path()}/scores.json.gz")
        infofile.load_data(default={})

        users: List[objects.LinkedPlayer] = userfile.data

        for user in users:
            if not user["full_tracking"]:
                continue
            if not exists(f"{self._get_path()}/scores/{user['user_id']}.json.gz"):
                return True
            if str(user["user_id"]) not in infofile.data:
                return True
            last_fetch = str_to_datetime(infofile.data[str(user["user_id"])])
            if (datetime.datetime.now() - last_fetch) > datetime.timedelta(days=7):
                return True
        return False

    def run(self) -> TaskStatus:
        userfile = DataFile(self._get_path_users())
        userfile.load_data(default=list())
        infofile = DataFile(f"{self._get_path()}/scores.json.gz")
        infofile.load_data(default={})

        users: List[objects.LinkedPlayer] = userfile.data

        for user in users:
            if self.suspended:
                return TaskStatus.SUSPENDED
            if not user["full_tracking"]:
                continue
            if str(user["user_id"]) in infofile.data:
                last_fetch = str_to_datetime(infofile.data[str(user["user_id"])])
                if (datetime.datetime.now() - last_fetch) < datetime.timedelta(days=7):
                    continue
            path = f"{self._get_path()}/scores/{user['user_id']}.json.gz"
            scorefile = DataFile(path)
            scorefile.load_data(default={})
            for name, gamemode in objects.gamemodes.items():
                scores, maps = akatsuki.get_user_best(
                    user["user_id"], gamemode, pages=1000
                )
                if not scorefile.data[name]:
                    scorefile.data[name] = dict()
                for score in scores:
                    scorefile.data[name][score["beatmap_id"]] = score
                save_beatmaps(maps)
            infofile.data[user["user_id"]] = datetime_to_str(datetime.datetime.now())
            scorefile.save_data()
            infofile.save_data()
        return self._finish()

    def _get_path(self):
        return f"{config['common']['data_directory']}/users_statistics/"

    def _get_path_users(self) -> str:
        return f"{config['common']['data_directory']}/users_statistics/users.json.gz"


class TrackUserPlaytime(Task):
    def __init__(self) -> None:
        super().__init__()
        self.last_fetch = datetime.datetime(year=2000, month=1, day=1)

    def can_run(self) -> bool:
        return (datetime.datetime.now() - self.last_fetch) > datetime.timedelta(
            minutes=30
        )

    def run(self) -> TaskStatus:
        self.last_fetch = datetime.datetime.now()
        userfile = DataFile(self._get_path_users())
        userfile.load_data(default=list())
        scorefile = DataFile(f"{self._get_path()}/scores.json.gz")
        scorefile.load_data(default={})

        users: List[objects.LinkedPlayer] = userfile.data

        for user in users:
            if self.suspended:
                return TaskStatus.SUSPENDED
            if not user["full_tracking"]:
                continue
            if str(user["user_id"]) not in scorefile.data:
                continue
            path = f"{self._get_path()}/scores/{user['user_id']}.json.gz"
            if not exists(path):
                continue
            scoredata = DataFile(path)
            scoredata.load_data(default={})
            userpt = DataFile(f"{self._get_path()}/playtime/{user['user_id']}.json.gz")
            userpt.load_data(default={})
            if not userpt.data:
                for name, gamemode in objects.gamemodes.items():
                    pt = {
                        "submitted_plays": 0,
                        "unsubmitted_plays": 0,
                    }
                    scores: List[objects.Score] = scoredata.data[name].values()
                    for score in scores:
                        divisor = 1.5 if (score["mods"] & 64) else 1
                        beatmap = load_beatmap(score["beatmap_id"])
                        if "attributes" in beatmap:
                            pt["submitted_plays"] += (
                                beatmap["attributes"]["length"] / divisor
                            )
                    userpt.data[name] = pt
            for name, gamemode in objects.gamemodes.items():
                skip = 0
                while True:
                    _scores, beatmaps = akatsuki.get_user_recent(
                        user["user_id"], gamemode, skip=skip, length=50
                    )
                    if not _scores:
                        break
                    save_beatmaps(beatmaps)
                    for score in _scores:
                        if str(score["beatmap_id"]) in scoredata.data[name]:
                            if (
                                score["id"]
                                == scoredata.data[name][str(score["beatmap_id"])]["id"]
                            ):
                                break
                        map = load_beatmap(score["beatmap_id"])
                        # if map["length"] == 0:  # blame akatsuki api
                        #    continue
                        divisor = 1.5 if (score["mods"] & 64) else 1
                        if score["completed"] == 3:  # personal best
                            scoredata.data[name][str(score["beatmap_id"])] = score
                            if "attributes" in map:
                                userpt.data[name]["submitted_plays"] += (
                                    map["attributes"]["length"] / divisor
                                )
                        else:
                            total_hits = (
                                score["count_300"]
                                + score["count_100"]
                                + score["count_50"]
                                + score["count_miss"]
                            )
                            if "attributes" in map:
                                multiplier = total_hits / map["attributes"]["max_combo"]
                                userpt.data[name]["unsubmitted_plays"] += (
                                    map["attributes"]["length"] / divisor
                                ) * multiplier
                    else:
                        skip += 1
                        continue
                    break

            userpt.save_data()
            scoredata.save_data()
        return self._finish()

    def _get_path(self):
        return f"{config['common']['data_directory']}/users_statistics/"

    def _get_path_users(self) -> str:
        return f"{config['common']['data_directory']}/users_statistics/users.json.gz"
