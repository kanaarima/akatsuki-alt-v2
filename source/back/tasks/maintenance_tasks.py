from ossapi.enums import BeatmapsetSearchSort, BeatmapsetSearchCategory
from api.utils import datetime_to_str, str_to_datetime, calculate_max_score
from api.files import DataFile, BinaryFile, exists
from datetime import datetime, timedelta
from api.tasks import Task, TaskStatus
from api.objects import gamemodes
import api.beatmaps as beatmaps
import api.akatsuki as akatsuki
from api.logging import get_logger
from config import config
import subprocess
import utils.api
import glob
import json
import time

logger = get_logger("tasks.maintenance")


class CheckNewRankedBeatmaps(Task):
    def __init__(self) -> None:
        super().__init__(asynchronous=True)
        self.last = datetime(year=1984, month=1, day=1)

    def can_run(self) -> bool:
        return (datetime.now() - self.last) > timedelta(days=1)

    def run(self) -> TaskStatus:
        self.last = datetime.now()
        sets = beatmaps.client.search_beatmapsets(
            mode=0,
            sort=BeatmapsetSearchSort.RANKED_DESCENDING,
            category=BeatmapsetSearchCategory.HAS_LEADERBOARD,
        )
        for set in sets.beatmapsets:
            for beatmap in set.beatmaps:
                beatmap._beatmapset = set
                if self.suspended:
                    return TaskStatus.SUSPENDED
                if not exists(f"{beatmaps.base_path}/{beatmap.id}.json.gz"):
                    logger.info(f"Found new ranked beatmap {beatmap.id}")
                    beatmaps.save_beatmap(
                        {"beatmap_id": beatmap.id, "raw_beatmap": beatmap}
                    )
        return self._finish()


class BuildBeatmapCache(Task):
    def __init__(self) -> None:
        super().__init__(asynchronous=True)
        self.last = datetime(year=1984, month=1, day=1)

    def can_run(self) -> bool:
        return (datetime.now() - self.last) > timedelta(hours=1)

    def run(self) -> TaskStatus:
        self.last = datetime.now()
        path = f"{config['common']['data_directory']}/beatmaps/"

        def cache_value():
            return {
                "star_rating": {},
                "length": {},
                "ar": {},
                "od": {},
                "cs": {},
                "tags": {},
                "mappers": {},
                "artists": {},
                "total": [],
            }

        cache = {
            "ranked": cache_value(),
            "loved": cache_value(),
            "ranked_akatsuki": cache_value(),
            "loved_akatsuki": cache_value(),
            "unranked": cache_value(),
            "metadata": {},
        }
        prev_state = beatmaps.cache_enabled
        beatmaps.cache_enabled = False
        for file in glob.glob(f"{path}*.json.gz"):
            if self.suspended:
                return TaskStatus.SUSPENDED
            beatmap_id = int(file.replace(path, "").replace(".json.gz", ""))
            if not exists(file.replace(".json.gz", ".osu.gz")):
                continue
            beatmap = beatmaps.load_beatmap(beatmap_id)
            key = "unranked"
            if "status" not in beatmap:
                continue
            if beatmap["status"]["bancho"] < 1:
                akatstatus = beatmap["status"]["akatsuki"]
                if akatstatus > 0 and akatstatus < 4:
                    key = "ranked_akatsuki"
                elif akatstatus == 4:
                    key = "loved_akatsuki"
            else:
                banchostatus = beatmap["status"]["bancho"]
                if banchostatus < 4 and banchostatus > 0:
                    key = "ranked"
                elif banchostatus == 4:
                    key = "loved"
            if "attributes" not in beatmap or beatmap["attributes"]["mode"] != 0:
                continue
            cache["metadata"][beatmap_id] = {
                "artist": beatmap["artist"],
                "title": beatmap["title"],
                "difficulty_name": beatmap["difficulty_name"],
                "length": beatmap["attributes"]["length"],
                "max_score": calculate_max_score(beatmap["attributes"]),
            }
            ar = str(int(beatmap["attributes"]["ar"]))
            if ar in cache[key]["ar"]:
                cache[key]["ar"][ar].append(beatmap_id)
            else:
                cache[key]["ar"][ar] = [beatmap_id]
            if not beatmap["attributes"]["od"]:  # Odd bug causes OD to be null
                continue
            od = str(int(beatmap["attributes"]["od"]))
            if od in cache[key]["od"]:
                cache[key]["od"][od].append(beatmap_id)
            else:
                cache[key]["od"][od] = [beatmap_id]
            cs = str(int(beatmap["attributes"]["cs"]))
            if cs in cache[key]["cs"]:
                cache[key]["cs"][cs].append(beatmap_id)
            else:
                cache[key]["cs"][cs] = [beatmap_id]
            length = int(beatmap["attributes"]["length"] / 60)
            if length == 0:
                if "<1" in cache[key]["length"]:
                    cache[key]["length"]["<1"].append(beatmap_id)
                else:
                    cache[key]["length"]["<1"] = [beatmap_id]
            else:
                length = str(length)
                if length in cache[key]["length"]:
                    cache[key]["length"][length].append(beatmap_id)
                else:
                    cache[key]["length"][length] = [beatmap_id]
            if "difficulty" in beatmap:
                sr = str(int(beatmap["difficulty"]["0"]["star_rating"]))
                if sr in cache[key]["star_rating"]:
                    cache[key]["star_rating"][sr].append(beatmap_id)
                else:
                    cache[key]["star_rating"][sr] = [beatmap_id]
            if beatmap["mapper"] in cache[key]["mappers"]:
                cache[key]["mappers"][beatmap["mapper"]].append(beatmap_id)
            else:
                cache[key]["mappers"][beatmap["mapper"]] = [beatmap_id]
            if beatmap["artist"].title() in cache[key]["artists"]:
                cache[key]["artists"][beatmap["artist"].title()].append(beatmap_id)
            else:
                cache[key]["artists"][beatmap["artist"].title()] = [beatmap_id]
            cache[key]["total"].append(beatmap_id)
            beatmap_raw = BinaryFile(file.replace(".json.gz", ".osu.gz"))
            beatmap_raw.load_data()
            beatmap_raw = beatmap_raw.data.decode("utf-8")
            for line in beatmap_raw.split("\n"):
                if line.startswith("Tags:"):
                    for tag in line[5:].split():
                        tag = tag.title()
                        if tag in cache[key]["tags"]:
                            cache[key]["tags"][tag].append(beatmap_id)
                        else:
                            cache[key]["tags"][tag] = [beatmap_id]

        def sort_dict(dikt, key, reverse):
            return dict(sorted(dikt.items(), key=key, reverse=reverse))

        for key in cache:
            if key == "metadata":
                continue
            cache[key]["star_rating"] = sort_dict(
                cache[key]["star_rating"], key=lambda x: int(x[0]), reverse=False
            )
            cache[key]["ar"] = sort_dict(
                cache[key]["ar"], key=lambda x: int(x[0]), reverse=False
            )
            cache[key]["od"] = sort_dict(
                cache[key]["od"], key=lambda x: int(x[0]), reverse=False
            )
            cache[key]["cs"] = sort_dict(
                cache[key]["cs"], key=lambda x: int(x[0]), reverse=False
            )
            cache[key]["length"] = sort_dict(
                cache[key]["length"],
                key=lambda x: int(x[0]) if x[0] != "<1" else 0,
                reverse=False,
            )
            cache[key]["tags"] = sort_dict(
                cache[key]["tags"], key=lambda x: len(x[1]), reverse=True
            )
            cache[key]["artists"] = sort_dict(
                cache[key]["artists"], key=lambda x: len(x[1]), reverse=True
            )
            cache[key]["mappers"] = sort_dict(
                cache[key]["mappers"], key=lambda x: len(x[1]), reverse=True
            )

        file = DataFile(f"{config['common']['data_directory']}/beatmap_cache.json.gz")
        file.data = cache
        file.save_data()
        beatmaps.cache_enabled = prev_state
        return self._finish()


class FixAkatsukiBeatmapRankings(Task):
    def __init__(self) -> None:
        super().__init__(asynchronous=True)
        self.last = datetime(year=1984, month=1, day=1)

    def can_run(self) -> bool:
        return (datetime.now() - self.last) > timedelta(days=1)

    def run(self) -> TaskStatus:
        self.last = datetime.now()
        path = f"{config['common']['data_directory']}/beatmaps/"
        for file in glob.glob(f"{path}*.json.gz"):
            if self.suspended:
                return TaskStatus.SUSPENDED
            beatmap_id = int(file.replace(path, "").replace(".json.gz", ""))
            beatmap = beatmaps.load_beatmap(beatmap_id)
            if "status" not in beatmap:
                continue  # Scuffed map?
            bancho_status = beatmap["status"]["bancho"]
            if bancho_status in [1, 2]:
                continue
            if "checked" in beatmap["status"]:
                if (
                    datetime.now() - str_to_datetime(beatmap["status"]["checked"])
                ) < timedelta(weeks=2):
                    continue
            if info := akatsuki.get_map_info(beatmap_id):
                beatmap["status"]["akatsuki"] = info["ranked"] - 1  # offset by 1
            beatmap["status"]["checked"] = datetime_to_str(datetime.now())
            beatmaps.save_beatmap(beatmap, overwrite=True, trustable=True)
            logger.info(
                f"Changed beatmap {beatmap_id} status from {bancho_status} to {beatmap['status']['akatsuki']}"
            )
        return self._finish()


class StoreTopPlays(Task):
    def __init__(self) -> None:
        super().__init__(asynchronous=False)

    def can_run(self) -> bool:
        return not exists(f"{config['common']['data_directory']}/scores.json.gz")

    def run(self) -> TaskStatus:
        scores_all = []
        for player, _, _ in akatsuki.get_user_leaderboard(
            gamemode=gamemodes["std_rx"], sort=akatsuki.Sort_Method.PP_ALL, pages=10
        ):
            scores, apimaps = akatsuki.get_user_best(
                player["id"], gamemodes["std_rx"], pages=4
            )
            scores_all.extend(scores)
            beatmaps.save_beatmaps(apimaps)
        file = DataFile(f"{config['common']['data_directory']}/scores.json.gz")
        file.data = scores_all
        file.save_data()
        return self._finish()


class CheckAkatsukiNominationChannel(Task):
    def __init__(self) -> None:
        super().__init__(asynchronous=True)

    def can_run(self) -> bool:
        last_checked_file = DataFile(
            f"{config['common']['data_directory']}/discord_crawler.json"
        )
        if last_checked_file.exists():
            last_checked_file.load_data()
            if (
                not last_checked_file.data
                or "last_checked" not in last_checked_file.data
            ):
                return True
            if (
                datetime.now() - str_to_datetime(last_checked_file.data["last_checked"])
            ) < timedelta(days=1):
                return False
        return True

    def run(self):
        dce_path = f"{config['discord_crawler']['discord_chat_exporter_dll_path']}"
        date = f"--after {(datetime.now() - timedelta(days=2)).date()}"
        last_checked_file = DataFile(
            f"{config['common']['data_directory']}/discord_crawler.json"
        )
        if not last_checked_file.exists():
            date = ""
        args = f"export -t {config['discord_crawler']['selfbot_token']} -c 597200076561055795 -f json -o {config['common']['cache_directory']}/messages.json"
        res = subprocess.Popen(
            f"dotnet {dce_path} {args} {date}",
            shell=True,
        )
        code = res.wait()
        if code != 0:
            logger.warning(f"Selfbot returned code {code}")
        mapsetids = []
        with open(f"{config['common']['cache_directory']}/messages.json") as f:
            data = json.load(f)
            for message in data["messages"]:
                if "https://osu.ppy.sh" not in message["content"]:
                    continue
                if not message["reactions"]:
                    continue
                text = message["content"]
                for string in text.split("/"):
                    if string.isnumeric():
                        mapsetids.append(int(string))
                        break
        logger.info(f"potentially found {len(mapsetids)} beatmap sets")
        i = 0
        for mapsetid in mapsetids:
            i += 1
            logger.debug(f"Remaining: {i} out of {len(mapsetids)} (ID: {mapsetid})")
            if self.suspended:
                return self._finish()
            try:
                mapset = beatmaps.client.beatmapset(beatmapset_id=mapsetid)
                beatmap._beatmapset = mapset
                if not exists(f"{beatmaps.base_path}/{beatmap.id}.json.gz"):
                    logger.info(f"Found new akatsuki beatmap {beatmap.id}")
                    beatmaps.save_beatmap(
                        {"beatmap_id": beatmap.id, "raw_beatmap": beatmap}
                    )
            except Exception:
                logger.warn(f"Skipping {mapsetid}")
                continue
            if not mapset:  # Sometimes they're deleted
                logger.info(f"Beatmap Set {mapsetid} is deleted!")
            for beatmap in mapset.beatmaps:
                time.sleep(1)
        last_checked_file.data = {"last_checked": datetime_to_str(datetime.now())}
        last_checked_file.save_data()


class CheckAkatsukiBeatmapsChannel(Task):
    def __init__(self) -> None:
        super().__init__(asynchronous=True)

    def can_run(self) -> bool:
        last_checked_file = DataFile(
            f"{config['common']['data_directory']}/discord_crawler_2.json"
        )
        if last_checked_file.exists():
            last_checked_file.load_data()
            if (
                not last_checked_file.data
                or "last_checked" not in last_checked_file.data
            ):
                return True
            if (
                datetime.now() - str_to_datetime(last_checked_file.data["last_checked"])
            ) < timedelta(days=1):
                return False
        return True

    def run(self):
        dce_path = f"{config['discord_crawler']['discord_chat_exporter_dll_path']}"
        date = f"--after {(datetime.now() - timedelta(days=2)).date()}"
        last_checked_file = DataFile(
            f"{config['common']['data_directory']}/discord_crawler_2.json"
        )
        if not last_checked_file.exists():
            date = ""
        args = f"export -t {config['discord_crawler']['selfbot_token']} -c 647363000629460992 -f json -o {config['common']['cache_directory']}/messages_2.json"
        res = subprocess.Popen(
            f"dotnet {dce_path} {args} {date}",
            shell=True,
        )
        code = res.wait()
        if code != 0:
            logger.warning(f"Selfbot returned code {code}")
        mapsetids = []
        with open(f"{config['common']['cache_directory']}/messages_2.json") as f:
            data = json.load(f)
            for message in data["messages"]:
                try:
                    if not message["embeds"]:
                        continue
                    embed = message["embeds"][0]
                    text = None
                    for field in embed["fields"]:
                        if "/d/" in field["value"]:
                            text = field["value"].replace(")", "").split("/")[-1]
                    if not text:
                        continue
                    for string in text.split("/"):
                        if string.isnumeric():
                            mapsetids.append(int(string))
                            break
                except:
                    logger.warn(f"cant process message ID {message['id']}")
        logger.info(f"potentially found {len(mapsetids)} beatmap sets")
        for i, mapsetid in enumerate(mapsetids, start=2700):
            logger.debug(f"Remaining: {i} out of {len(mapsetids)} (ID: {mapsetid})")
            if self.suspended:
                return self._finish()
            try:
                mapset = beatmaps.client.beatmapset(beatmapset_id=mapsetid)
                if not mapset:  # Sometimes they're deleted
                    logger.info(f"Beatmap Set {mapsetid} is deleted!")
                for beatmap in mapset.beatmaps:
                    beatmap._beatmapset = mapset
                    if not exists(f"{beatmaps.base_path}/{beatmap.id}.json.gz"):
                        logger.info(f"Found new akatsuki beatmap {beatmap.id}")
                        beatmaps.save_beatmap(
                            {"beatmap_id": beatmap.id, "raw_beatmap": beatmap}
                        )
                time.sleep(1)
            except BaseException:
                logger.error(f"Skipping {mapsetid}", exc_info=True)
        last_checked_file.data = {"last_checked": datetime_to_str(datetime.now())}
        last_checked_file.save_data()
