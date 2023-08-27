from ossapi.enums import BeatmapsetSearchSort, BeatmapsetSearchCategory
from api.files import DataFile, BinaryFile, exists
from datetime import datetime, timedelta
from api.tasks import Task, TaskStatus
import api.beatmaps as beatmaps
from api.logging import logger
from config import config
import glob


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
        return (datetime.now() - self.last) > timedelta(days=1)

    def run(self) -> TaskStatus:
        self.last = datetime.now()
        path = f"{config['common']['data_directory']}/beatmaps/"
        cache = {
            "star_rating": dict(),
            "length": dict(),
            "ar": dict(),
            "od": dict(),
            "cs": dict(),
            "tags": dict(),
            "mappers": dict(),
            "artists": dict(),
        }
        for file in glob.glob(f"{path}*.osu.gz"):
            if self.suspended:
                return
            beatmap_id = int(file.replace(path, "").replace(".osu.gz", ""))
            if not exists(file.replace(".osu.gz", ".json.gz")):
                beatmaps.download_beatmap(beatmap_id)
            beatmap = beatmaps.load_beatmap(beatmap_id)
            beatmaps.cache = {}
            if "attributes" not in beatmap or beatmap["attributes"]["mode"] != 0:
                continue
            else:
                ar = str(int(beatmap["attributes"]["ar"]))
                if ar in cache["ar"]:
                    cache["ar"][ar].append(beatmap_id)
                else:
                    cache["ar"][ar] = [beatmap_id]
                od = str(int(beatmap["attributes"]["od"]))
                if od in cache["od"]:
                    cache["od"][od].append(beatmap_id)
                else:
                    cache["od"][od] = [beatmap_id]
                cs = str(int(beatmap["attributes"]["cs"]))
                if cs in cache["cs"]:
                    cache["cs"][cs].append(beatmap_id)
                else:
                    cache["cs"][cs] = [beatmap_id]
                length = int(beatmap["attributes"]["length"] / 60)
                if length == 0:
                    if "<1" in cache["length"]:
                        cache["length"]["<1"].append(beatmap_id)
                    else:
                        cache["length"]["<1"] = [beatmap_id]
                else:
                    length = str(length)
                    if length in cache["length"]:
                        cache["length"][length].append(beatmap_id)
                    else:
                        cache["length"][length] = [beatmap_id]
            if "difficulty" in beatmap:
                sr = str(int(beatmap["difficulty"]["0"]["star_rating"]))
                if sr in cache["star_rating"]:
                    cache["star_rating"][sr].append(beatmap_id)
                else:
                    cache["star_rating"][sr] = [beatmap_id]
            if beatmap["mapper"] in cache["mappers"]:
                cache["mappers"][beatmap["mapper"]].append(beatmap_id)
            else:
                cache["mappers"][beatmap["mapper"]] = [beatmap_id]
            if beatmap["artist"].title() in cache["artists"]:
                cache["artists"][beatmap["artist"].title()].append(beatmap_id)
            else:
                cache["artists"][beatmap["artist"].title()] = [beatmap_id]
            beatmap_raw = BinaryFile(file)
            beatmap_raw.load_data()
            beatmap_raw = beatmap_raw.data.decode("utf-8")
            for line in beatmap_raw.split("\n"):
                if line.startswith("Tags:"):
                    for tag in line[5:].split():
                        tag = tag.title()
                        if tag in cache["tags"]:
                            cache["tags"][tag].append(beatmap_id)
                        else:
                            cache["tags"][tag] = [beatmap_id]

        def sort_dict(dikt, key, reverse):
            return dict(sorted(dikt.items(), key=key, reverse=reverse))

        cache["star_rating"] = sort_dict(
            cache["star_rating"], key=lambda x: int(x[0]), reverse=False
        )
        cache["ar"] = sort_dict(cache["ar"], key=lambda x: int(x[0]), reverse=False)
        cache["od"] = sort_dict(cache["od"], key=lambda x: int(x[0]), reverse=False)
        cache["cs"] = sort_dict(cache["cs"], key=lambda x: int(x[0]), reverse=False)
        cache["length"] = sort_dict(
            cache["length"],
            key=lambda x: int(x[0]) if x[0] != "<1" else 0,
            reverse=False,
        )
        cache["tags"] = sort_dict(cache["tags"], key=lambda x: len(x[1]), reverse=True)
        cache["artists"] = sort_dict(
            cache["artists"], key=lambda x: len(x[1]), reverse=True
        )
        cache["mappers"] = sort_dict(
            cache["mappers"], key=lambda x: len(x[1]), reverse=True
        )

        file = DataFile(f"{config['common']['data_directory']}/beatmap_cache.json.gz")
        file.data = cache
        file.save_data()
        return self._finish()
