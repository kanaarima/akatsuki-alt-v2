from api.utils import (
    yesterday,
    find_unique,
    datetime_to_str,
    str_to_datetime,
)
from api.beatmaps import save_beatmaps, load_beatmap, get_by_leaderboard
from api.utils import str_to_datetime, datetime_to_str
from api.tasks import Task, TaskStatus
from api.files import DataFile, exists
from api import objects, akatsuki
from api.logging import get_logger
import api.database as database
import api.events as events
from config import config
from typing import List
import datetime
import glob
import time

logger = get_logger("tasks.users")


class StoreUserLeaderboardsTask(Task):
    def __init__(self) -> None:
        super().__init__()

    def can_run(self) -> bool:
        return not exists(self._get_path())

    def run(self) -> TaskStatus:
        data = {}
        for name, gamemode in objects.gamemodes.items():
            data[name] = []
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
        return not exists(self._get_path())

    def run(self) -> TaskStatus:
        cur = database.ConnectionHandler()
        for user_id in cur.execute("SELECT user_id FROM users"):
            user_id = user_id[0]
            userfile = DataFile(filepath=f"{self._get_path()}{user_id}.json.gz")
            userfile.data = {}
            player, stats = akatsuki.get_user_stats(user_id)
            first_places = {}
            for name, gamemode in objects.gamemodes.items():
                playtime = cur.execute(
                    "SELECT submitted_plays, unsubmitted_plays, most_played FROM users_playtime WHERE user_id = ? AND mode = ?",
                    (user_id, name),
                ).fetchall()
                if playtime:
                    stats[name][0]["play_time"] = (
                        playtime[0][0] + playtime[0][1] + playtime[0][2]
                    )
                clears = cur.execute(
                    "SELECT COUNT(score_id) FROM users_scores WHERE user_id = ? AND mode = ?",
                    (user_id, name),
                ).fetchall()
                if clears:
                    stats[name][0]["clears"] = clears[0][0]
                _, first_places[name], beatmaps = akatsuki.get_user_1s(
                    userid=user_id,
                    gamemode=gamemode,
                    pages=1000,
                )
                save_beatmaps(beatmaps)
            userfile.data["player"] = player
            userfile.data["statistics"] = stats
            userfile.data["first_places"] = first_places
            userfile.save_data()
        cur.close()
        return self._finish()

    def _get_path(self) -> str:
        return f"{config['common']['data_directory']}/users_statistics/{yesterday()}/"


class StorePlayerScores(Task):
    def __init__(self) -> None:
        super().__init__(asynchronous=False)

    def can_run(self) -> bool:
        cur = database.ConnectionHandler()
        for user_id in cur.execute("SELECT user_id FROM users").fetchall():
            user_id = user_id[0]
            if not cur.execute(
                "SELECT user_id FROM users_scores WHERE user_id = ?", (user_id,)
            ).fetchone():
                cur.close()
                return True
        return False

    def run(self) -> TaskStatus:
        cur = database.ConnectionHandler()
        for user_id in cur.execute("SELECT user_id FROM users").fetchall():
            user_id = user_id[0]
            if self.suspended:
                return TaskStatus.SUSPENDED

            if cur.execute(
                "SELECT user_id FROM users_scores WHERE user_id = ?", (user_id,)
            ).fetchone():
                continue  # recent scores fetch is 100% accurate, no need

            for name, gamemode in objects.gamemodes.items():
                scores, maps = akatsuki.get_user_best(user_id, gamemode, pages=1000)
                for score in scores:
                    cur.execute(
                        "INSERT OR REPLACE INTO users_scores VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            score["beatmap_id"],
                            name,
                            score["id"],
                            user_id,
                            score["accuracy"],
                            score["mods"],
                            score["pp"],
                            score["score"],
                            score["combo"],
                            score["rank"],
                            score["count_300"],
                            score["count_100"],
                            score["count_50"],
                            score["count_miss"],
                            score["date"],
                        ),
                    )
                save_beatmaps(maps)
        cur.close()
        return self._finish()

    def _get_path(self):
        return f"{config['common']['data_directory']}/users_statistics/"


class TrackUserPlaytime(Task):
    def __init__(self) -> None:
        super().__init__()

    def can_run(self) -> bool:
        last_checked = datetime.datetime.fromtimestamp(
            database.get_task("trackuserplaytime")
        )
        return (datetime.datetime.now() - last_checked) > datetime.timedelta(minutes=10)

    def run(self) -> TaskStatus:
        database.set_task("trackuserplaytime", time.time())
        cur = database.ConnectionHandler()
        for user_id in cur.execute("SELECT user_id FROM users").fetchall():
            user_id = user_id[0]
            if self.suspended:
                return TaskStatus.SUSPENDED
            if not cur.execute(
                "SELECT user_id FROM users_scores WHERE user_id = ?", (user_id,)
            ).fetchone():
                continue
            playtime = cur.execute(
                "SELECT * FROM users_playtime WHERE user_id = ?",
                (user_id,),
            ).fetchall()
            if not playtime:
                for name, gamemode in objects.gamemodes.items():
                    pt = {
                        "submitted_plays": 0,
                        "unsubmitted_plays": 0,
                        "most_played": 0,
                        "last_score_id": 0,
                    }
                    scores = cur.execute(
                        "SELECT beatmap_id, mods FROM users_scores WHERE user_id = ? AND mode = ?",
                        (user_id, name),
                    ).fetchall()
                    for score in scores:
                        divisor = 1.5 if (score[1] & 64) else 1
                        beatmap = load_beatmap(score[0])
                        if "attributes" in beatmap:
                            pt["submitted_plays"] += (
                                beatmap["attributes"]["length"] / divisor
                            )
                    self._add_most_played(user_id, pt, name, gamemode)
                    cur.execute(
                        "INSERT INTO users_playtime VALUES(?,?,?,?,?,?)",
                        (
                            user_id,
                            name,
                            pt["submitted_plays"],
                            pt["unsubmitted_plays"],
                            pt["most_played"],
                            0,
                        ),
                    )
                    database.conn.commit()
            for name, gamemode in objects.gamemodes.items():
                last_score_id = cur.execute(
                    "SELECT last_score_id FROM users_playtime WHERE user_id = ? and mode = ?",
                    (user_id, name),
                ).fetchall()[0][0]
                skip = 0
                old_id = last_score_id
                while True:
                    _scores, beatmaps = akatsuki.get_user_recent(
                        user_id, gamemode, skip=skip, length=50
                    )
                    if not _scores:
                        break
                    save_beatmaps(beatmaps)
                    exit = False
                    for score in _scores:
                        if int(score["id"]) == old_id:
                            exit = True
                            break
                        map = load_beatmap(score["beatmap_id"])
                        # if map["length"] == 0:  # blame akatsuki api
                        #    continue
                        divisor = 1.5 if (score["mods"] & 64) else 1
                        if score["completed"] == 3:  # personal best
                            new = not cur.execute(
                                "SELECT beatmap_id FROM users_scores WHERE user_id = ? AND mode = ? AND beatmap_id = ?",
                                (user_id, name, score["beatmap_id"]),
                            ).fetchone()
                            cur.execute(
                                "INSERT OR REPLACE INTO users_scores VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                (
                                    score["beatmap_id"],
                                    name,
                                    score["id"],
                                    user_id,
                                    score["accuracy"],
                                    score["mods"],
                                    score["pp"],
                                    score["score"],
                                    score["combo"],
                                    score["rank"],
                                    score["count_300"],
                                    score["count_100"],
                                    score["count_50"],
                                    score["count_miss"],
                                    score["date"],
                                ),
                            )
                            if "attributes" in map:
                                cur.execute(
                                    """UPDATE users_playtime SET "submitted_plays" = submitted_plays+? WHERE user_id = ? AND mode = ?""",
                                    (
                                        map["attributes"]["length"] / divisor,
                                        user_id,
                                        name,
                                    ),
                                )
                                database.conn.commit()
                            self._check_if_top_play(
                                user_id=user_id,
                                score=score,
                                gamemode=name,
                                new=new,
                            )
                        elif "attributes" in map:
                            total_hits = (
                                score["count_300"]
                                + score["count_100"]
                                + score["count_50"]
                                + score["count_miss"]
                            )
                            if not map["attributes"]["max_combo"]:
                                logger.warn(f"Bugged map {map['beatmap_id']}")
                                continue
                            multiplier = total_hits / map["attributes"]["max_combo"]
                            cur.execute(
                                """UPDATE users_playtime SET "unsubmitted_plays" = unsubmitted_plays+? WHERE user_id = ? AND mode = ?""",
                                (
                                    (map["attributes"]["length"] / divisor)
                                    * multiplier,
                                    user_id,
                                    name,
                                ),
                            )
                    if skip == 0:
                        cur.execute(
                            """UPDATE users_playtime SET "last_score_id" = ? WHERE user_id = ? AND mode = ?""",
                            (
                                int(_scores[0]["id"]),
                                user_id,
                                name,
                            ),
                        )
                    if exit:
                        break
                    else:
                        skip += 1

            database.conn.commit()
        cur.close()
        return self._finish()

    def _add_most_played(self, userid: int, pt, name, gamemode):
        pt["most_played"] = 0
        for playcount, apibeatmap in akatsuki.get_user_most_played(
            userid=userid, gamemode=gamemode, pages=10000
        ):
            beatmap = load_beatmap(apibeatmap["beatmap_id"])
            if (
                not beatmap
                or "attributes" not in beatmap
                or not beatmap["attributes"]["max_combo"]
            ):
                logger.warning(
                    f"Skipping {apibeatmap['beatmap_id']} for user {userid}!"
                )
                continue
            multiplier = 100 / beatmap["attributes"]["max_combo"]
            pt["most_played"] += (
                beatmap["attributes"]["length"] * multiplier
            ) * playcount

    def _check_if_top_play(
        self,
        user_id: int,
        score: objects.Score,
        gamemode: str,
        new: bool,
    ):
        logger.info(f"{user_id} set play {score['id']}")
        # TODO: Fix this hack someday
        scores = list()
        cur = database.ConnectionHandler()
        for _score in cur.execute(
            "SELECT beatmap_id, score_id, score, pp FROM users_scores WHERE user_id = ? AND mode = ?",
            (user_id, gamemode),
        ):
            scores.append(
                {
                    "beatmap_id": _score[0],
                    "id": _score[1],
                    "score": _score[2],
                    "pp": _score[3],
                }
            )
        ranked_scores = 0
        if len(scores) % 100 == 0 and new:
            event = events.top_play_event(
                user_id=user_id,
                beatmap_id=score["beatmap_id"],
                score=score,
                index=len(scores),
                gamemode=gamemode,
                play_type="clears",
            )
            events.send_event(target="frontend", event=event)
        for user_score in sorted(scores, key=lambda x: x["pp"], reverse=True):
            beatmap = load_beatmap(user_score["beatmap_id"])
            if not beatmap or "status" not in beatmap:
                continue
            ranked_scores += 1
            if score["id"] == user_score["id"]:
                event = events.top_play_event(
                    user_id=user_id,
                    beatmap_id=beatmap["beatmap_id"],
                    score=score,
                    index=ranked_scores,
                    gamemode=gamemode,
                    play_type="pp",
                )
                events.send_event(target="frontend", event=event)
            if ranked_scores == 120:
                break
        ranked_scores = 0
        for user_score in sorted(scores, key=lambda x: x["score"], reverse=True):
            beatmap = load_beatmap(user_score["beatmap_id"])
            if not beatmap or "status" not in beatmap:
                continue
            ranked_scores += 1
            if score["id"] == user_score["id"]:
                event = events.top_play_event(
                    user_id=user_id,
                    beatmap_id=beatmap["beatmap_id"],
                    score=score,
                    index=ranked_scores,
                    gamemode=gamemode,
                    play_type="score",
                )
                events.send_event(target="frontend", event=event)
            if ranked_scores == 100:
                break

    def _get_path(self):
        return f"{config['common']['data_directory']}/users_statistics/"


class CrawlLovedMaps(Task):
    def __init__(self) -> None:
        super().__init__()

    def can_run(self) -> bool:
        last_run = datetime.datetime.fromtimestamp(database.get_task("crawllovedmaps"))
        return (datetime.datetime.now() - last_run) > datetime.timedelta(days=7)

    def run(self):
        database.set_task("crawllovedmaps", time.time())
        cur = database.ConnectionHandler()
        leaderboards = get_by_leaderboard(["loved_bancho", "loved_akatsuki"])
        loved_maps = leaderboards["loved_bancho"] + leaderboards["loved_akatsuki"]
        logger.info(f"Crawling {len(loved_maps)} maps")
        userid = cur.execute("SELECT DISTINCT user_id FROM users_scores").fetchall()[0]
        for loved_map in loved_maps:
            scores = akatsuki.get_map_leaderboard(
                loved_map, objects.gamemodes["std_rx"], pages=10000
            )
            for player, score in scores:
                if player["id"] in userid:
                    if cur.execute(
                        "SELECT user_id FROM users_scores WHERE score_id = ?",
                        (score["id"],),
                    ).fetchall():
                        continue
                    logger.info(f"Found score on {loved_map} by {player['id']}")
                    cur.execute(
                        "INSERT OR REPLACE INTO users_scores VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            score["beatmap_id"],
                            "std_rx",
                            score["id"],
                            player["id"],
                            score["accuracy"],
                            score["mods"],
                            score["pp"],
                            score["score"],
                            score["combo"],
                            score["rank"],
                            score["count_300"],
                            score["count_100"],
                            score["count_50"],
                            score["count_miss"],
                            score["date"],
                        ),
                    )
        cur.close()
        return self._finish()


class CrawlMaps(Task):
    def __init__(self) -> None:
        super().__init__(asynchronous=True)

    def can_run(self) -> bool:
        return True

    def run(self):
        cur_main = database.ConnectionHandler()
        cur = database.ConnectionHandler(database.conn_lb)
        beatmap_ids = cur_main.execute(
            "SELECT beatmap_id FROM beatmaps WHERE akatsuki_status BETWEEN 1 AND 4 AND MODE = 0"
        ).fetchall()
        cur_main.close()
        for beatmap_id in beatmap_ids:
            beatmap_id = beatmap_id[0]
            if self.suspended:
                return self._finish()
            check = cur.execute(
                "SELECT last_update FROM beatmaps_leaderboard WHERE beatmap_id = ?",
                (beatmap_id,),
            ).fetchall()
            if check:
                if (
                    datetime.datetime.now()
                    - datetime.datetime.fromtimestamp(check[0][0])
                ) < datetime.timedelta(days=7):
                    continue
            logger.info(f"crawling {beatmap_id}")
            leaderboard = akatsuki.get_map_leaderboard(
                beatmap_id, gamemode=objects.gamemodes["std_rx"]
            )
            if not leaderboard:
                logger.info(f"Empty leaderboard: {beatmap_id}")
                continue
            i = 0
            for player, score in leaderboard[:50]:
                i += 1
                query = """INSERT OR REPLACE into "main"."beatmaps_leaderboard"("beatmap_id", "mode", "last_update", "position", "user_id", "accuracy", "mods", "pp", "score", "combo", "rank", "count_300", "count_100", "count_50", "count_miss", "date") VALUES (?, ?, ?,  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?); """
                cur.execute(
                    query,
                    (
                        beatmap_id,
                        "std_rx",
                        int(time.time()),
                        i,
                        player["id"],
                        score["accuracy"],
                        score["mods"],
                        score["pp"],
                        score["score"],
                        score["combo"],
                        score["rank"],
                        score["count_300"],
                        score["count_100"],
                        score["count_50"],
                        score["count_miss"],
                        score["date"],
                    ),
                )
                database.conn.commit()
            time.sleep(0.8)
        cur.close
        return self._finish()
