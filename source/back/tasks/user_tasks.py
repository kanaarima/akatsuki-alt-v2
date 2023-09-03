from api.utils import (
    yesterday,
    find_unique,
    datetime_to_str,
    str_to_datetime,
)
from api.beatmaps import save_beatmaps, save_beatmap, load_beatmap
from api.utils import str_to_datetime, datetime_to_str
from api.tasks import Task, TaskStatus
from api.files import DataFile, exists
from api import objects, akatsuki
from api.ordr import send_render
from api.logging import logger
import api.events as events
from config import config
from typing import List
import datetime
import glob


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
            playtime = DataFile(
                f"{config['common']['data_directory']}/users_statistics/playtime/{user['user_id']}.json.gz"
            )
            clears = DataFile(
                f"{config['common']['data_directory']}/users_statistics/scores/{user['user_id']}.json.gz"
            )
            clears.load_data(default=None)
            playtime.load_data(default=None)
            playtime = playtime.data
            player, stats = akatsuki.get_user_stats(user["user_id"])
            first_places = dict()
            for name, gamemode in objects.gamemodes.items():
                if playtime and "most_played" in playtime:
                    stats[name][0]["play_time"] = playtime[name]["most_played"]
                +playtime[name]["unsubmitted_plays"]
                +playtime[name]["submitted_plays"]
                if clears.data:
                    stats[name][0]["clears"] = len(clears.data[name])
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
                if name not in scorefile.data or not scorefile.data[name]:
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
            minutes=10
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
                        "most_played": 0,
                    }
                    scores: List[objects.Score] = scoredata.data[name].values()
                    for score in scores:
                        divisor = 1.5 if (score["mods"] & 64) else 1
                        beatmap = load_beatmap(score["beatmap_id"])
                        if "attributes" in beatmap:
                            pt["submitted_plays"] += (
                                beatmap["attributes"]["length"] / divisor
                            )
                    self._add_most_played(user["user_id"], pt, name, gamemode)
                    userpt.data[name] = pt
            for name, gamemode in objects.gamemodes.items():
                if "most_played" not in userpt.data[name]:
                    self._add_most_played(
                        user["user_id"], userpt.data[name], name, gamemode
                    )
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
                            if name == "std_rx":
                                self._check_renderable(
                                    user, list(scoredata.data[name].values()), score
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

    def _add_most_played(self, userid: int, pt, name, gamemode):
        pt["most_played"] = 0
        for playcount, apibeatmap in akatsuki.get_user_most_played(
            userid=userid, gamemode=gamemode, pages=10000
        ):
            save_beatmap(apibeatmap)
            beatmap = load_beatmap(apibeatmap["beatmap_id"])
            if (
                not beatmap
                or "attributes" not in beatmap
                or beatmap["attributes"]["max_combo"] == 0
            ):
                logger.warning(
                    f"Skipping {apibeatmap['beatmap_id']} for user {userid}!"
                )
                continue
            multiplier = 100 / beatmap["attributes"]["max_combo"]
            pt["most_played"] += (
                beatmap["attributes"]["length"] * multiplier
            ) * playcount

    def _check_renderable(
        self,
        user: objects.LinkedPlayer,
        scores: List[objects.Score],
        score: objects.Score,
    ):
        if "render_permission" not in user or not user["render_permission"]:
            return
        sorted_by_pp = list()
        for score_pp in sorted(scores, key=lambda x: x["pp"], reverse=True):
            beatmap = load_beatmap(score["beatmap_id"])
            if "status" in beatmap:
                status = beatmap["status"]["akatsuki"]
                # https://circleguard.github.io/ossapi/appendix.html#ossapi.enums.RankStatus
                if status != 2 and status != 1:
                    continue
                sorted_by_pp.append(score_pp)
            if len(sorted_by_pp) == 100:
                break
        for score_pp in sorted_by_pp:
            logger.info(f"rendering play {score['id']} by {user['id']}")
            if score_pp["id"] == score["id"]:  # Renderable
                logger.info(f"User {user['user_id']} set a new top 100 play!")
                player = akatsuki.get_user_info(user["user_id"])
                renderurl = send_render(
                    replayURL=f"https://akatsuki.gg/web/replays/{score['id']}",
                    username=player["name"],
                )
                if renderurl:
                    events.send_event(
                        "frontend", events.render_event(user["user_id"], renderurl)
                    )
                else:
                    logger.error(f"Failed rendering top play! {score['id']}")
                break

    def _get_path(self):
        return f"{config['common']['data_directory']}/users_statistics/"

    def _get_path_users(self) -> str:
        return f"{config['common']['data_directory']}/users_statistics/users.json.gz"


class CrawlLovedMaps(Task):
    def __init__(self) -> None:
        super().__init__()

    def can_run(self) -> bool:
        last_run = DataFile(
            f"{config['common']['data_directory']}/loved_crawler.json.gz"
        )
        last_run.load_data(
            default={
                "last_run": datetime_to_str(
                    datetime.datetime(year=2000, month=1, day=1)
                )
            }
        )
        return (
            datetime.datetime.now() - str_to_datetime(last_run.data["last_run"])
        ) > datetime.timedelta(days=3)

    def run(self):
        last_run = DataFile(
            f"{config['common']['data_directory']}/loved_crawler.json.gz"
        )
        last_run.load_data()
        last_run.data["last_run"] = datetime_to_str(datetime.datetime.now())
        last_run.save_data()
        cache = DataFile(f"{config['common']['data_directory']}/beatmap_cache.json.gz")
        cache.load_data()
        loved_maps = (
            cache.data["loved"]["total"] + cache.data["loved_akatsuki"]["total"]
        )
        logger.info(f"Crawling {len(loved_maps)} maps")
        path = f"{config['common']['data_directory']}/users_statistics/scores/"
        userid = {}
        for file in glob.glob(f"{path}*.json.gz"):
            userid[int(file.replace(path, "").replace(".json.gz", ""))] = file
        for loved_map in loved_maps:
            scores = akatsuki.get_map_leaderboard(
                loved_map, objects.gamemodes["std_rx"], pages=10000
            )
            for player, score in scores:
                if player["id"] in userid:
                    scorefile = DataFile(userid[player["id"]])
                    scorefile.load_data()
                    if str(score["beatmap_id"]) in scorefile.data["std_rx"]:
                        continue
                    logger.info(f"Found score on {loved_map} by {player['id']}")
                    scorefile.data["std_rx"][str(score["beatmap_id"])] = score
                    scorefile.save_data()
        return self._finish()
