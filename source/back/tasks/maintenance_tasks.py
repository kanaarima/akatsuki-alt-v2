from ossapi.enums import BeatmapsetSearchSort, BeatmapsetSearchCategory
from api.utils import datetime_to_str, str_to_datetime, calculate_max_score
from api.files import DataFile, BinaryFile, exists
from datetime import datetime, timedelta
from api.tasks import Task, TaskStatus
from api.objects import gamemodes
import api.beatmaps as beatmaps
import api.akatsuki as akatsuki
from api.logging import logger
from config import config
import utils.api
import glob

ask_peppy = utils.api.ApiHandler(base_url="https://akatsuki.gg/api/", delay=4)


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
                "star_rating": dict(),
                "length": dict(),
                "ar": dict(),
                "od": dict(),
                "cs": dict(),
                "tags": dict(),
                "mappers": dict(),
                "artists": dict(),
                "total": list(),
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
            else:
                if beatmap["status"]["bancho"] < 1:
                    akatstatus = beatmap["status"]["akatsuki"]
                    if akatstatus < 3:
                        key = "ranked_akatsuki"
                    elif akatstatus == 4:
                        key = "loved_akatsuki"
                else:
                    banchostatus = beatmap["status"]["bancho"]
                    if banchostatus < 3:
                        key = "ranked"
                    elif banchostatus == 4:
                        key = "loved"
            if "attributes" not in beatmap or beatmap["attributes"]["mode"] != 0:
                continue
            else:
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

        for key in cache.keys():
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
            if bancho_status == 1 or bancho_status == 2:
                continue
            if "checked" in beatmap["status"]:
                if (
                    datetime.now() - str_to_datetime(beatmap["status"]["checked"])
                ) < timedelta(weeks=2):
                    continue
            info = ask_peppy.get_request(f"get_beatmaps?limit=1&b={beatmap_id}")
            if info.status_code != 200 or not info.json():
                continue
            beatmap["status"]["akatsuki"] = int(info.json()[0]["approved"])
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
        scores_all = list()
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
