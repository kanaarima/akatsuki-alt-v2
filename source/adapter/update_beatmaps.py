import api.database as db
import api.beatmaps as beatmaps
from ossapi.enums import BeatmapsetSearchSort, BeatmapsetSearchCategory


def update_table():
    db.conn.execute("ALTER TABLE beatmaps ADD COLUMN approved_date INTEGER DEFAULT 0")
    db.conn.execute("ALTER TABLE beatmaps ADD COLUMN tags_packs TEXT DEFAULT ''")


def search_maps():
    cursor = None
    while True:
        sets = beatmaps.client.search_beatmapsets(
            mode=0,
            sort=BeatmapsetSearchSort.RANKED_DESCENDING,
            category=BeatmapsetSearchCategory.HAS_LEADERBOARD,
            cursor=cursor,
        )
        cursor = sets.cursor
        for set in sets.beatmapsets:
            for beatmap in set.beatmaps:
                beatmap._beatmapset = set
                if not db.conn.execute(
                    "SELECT * FROM beatmaps WHERE beatmap_id = ?", (beatmap.id,)
                ).fetchall():
                    continue
                tags_packs = ",".join(set.pack_tags) if set.pack_tags else ""
                approved_date = (
                    int(set.ranked_date.timestamp()) if set.ranked_date else 0
                )
                print(f"Updating {beatmap.id}: {approved_date} {tags_packs}")
                db.conn.execute(
                    "UPDATE beatmaps SET tags_packs = ? WHERE beatmap_id = ?",
                    (tags_packs, beatmap.id),
                )
                db.conn.execute(
                    "UPDATE beatmaps SET approved_date = ? WHERE beatmap_id = ?",
                    (approved_date, beatmap.id),
                )
                db.conn.commit()
                print(
                    f"Result: {db.conn.execute('SELECT * FROM beatmaps WHERE beatmap_id = ?', (beatmap.id,))}"
                )
