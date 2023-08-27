from api.tasks import Task, TaskStatus
from api.files import DataFile, exists
from datetime import datetime, timedelta
import api.beatmaps as beatmaps
from api.logging import logger
from ossapi.enums import BeatmapsetSearchSort, BeatmapsetSearchCategory


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
