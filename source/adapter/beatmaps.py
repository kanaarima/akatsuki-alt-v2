from api.beatmaps import base_path, process_beatmap
from api.files import BinaryFile, DataFile
from api.logging import get_logger
import api.database as database
from api.objects import Beatmap
import api.utils as utils
from config import config
import datetime
import hashlib
import glob
import os

logger = get_logger("api.adapter")


def non_null(val):
    return 0 if not val else val


def insert_beatmap(db, beatmap: Beatmap):
    query = """INSERT OR REPLACE INTO "main"."beatmaps" ("beatmap_id", "beatmap_set_id", "md5", "artist", "title", "difficulty_name", "mapper", "bancho_status", "akatsuki_status", "last_checked", "ar", "od", "cs", "length", "bpm", "max_combo", "circles", "sliders", "spinners", "mode", "tags", "stars_nm", "stars_ez", "stars_hr", "stars_dt", "stars_dtez", "stars_dthr") VALUES (?, ?, ?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?);"""
    query_nodiff = """INSERT OR REPLACE INTO "main"."beatmaps" ("beatmap_id", "beatmap_set_id", "md5", "artist", "title", "difficulty_name", "mapper", "bancho_status", "akatsuki_status", "last_checked", "ar", "od", "cs", "length", "bpm", "max_combo", "circles", "sliders", "spinners", "mode", "tags") VALUES (?, ?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
    last_checked = None
    if "checked" in beatmap["status"]:
        last_checked = beatmap["status"]["checked"]
    else:
        last_checked = utils.datetime_to_str(
            datetime.datetime(year=1984, month=1, day=1)
        )
    args = [
        beatmap["beatmap_id"],
        beatmap["beatmap_set_id"],
        beatmap["md5"],
        beatmap["artist"],
        beatmap["title"],
        beatmap["difficulty_name"],
        beatmap["mapper"],
        beatmap["status"]["bancho"],
        beatmap["status"]["akatsuki"],
        last_checked,
        non_null(beatmap["attributes"]["ar"]),
        non_null(beatmap["attributes"]["od"]),
        non_null(beatmap["attributes"]["cs"]),
        non_null(beatmap["attributes"]["length"]),
        non_null(beatmap["attributes"]["bpm"]),
        non_null(beatmap["attributes"]["max_combo"]),
        non_null(beatmap["attributes"]["circles"]),
        non_null(beatmap["attributes"]["sliders"]),
        non_null(beatmap["attributes"]["spinners"]),
        non_null(beatmap["attributes"]["mode"]),
        beatmap["tags"],
    ]
    if "difficulty" in beatmap:
        args.append(beatmap["difficulty"]["0"]["star_rating"])
        args.append(beatmap["difficulty"][str(utils.Easy)]["star_rating"])
        args.append(beatmap["difficulty"][str(utils.HardRock)]["star_rating"])
        args.append(beatmap["difficulty"][str(utils.DoubleTime)]["star_rating"])
        args.append(
            beatmap["difficulty"][str(utils.Easy + utils.DoubleTime)]["star_rating"]
        )
        args.append(
            beatmap["difficulty"][str(str(utils.HardRock + utils.DoubleTime))][
                "star_rating"
            ]
        )
        db.execute(query, args)
    else:
        db.execute(query_nodiff, args)

    db.close()


def main():
    for file in glob.glob(f"{base_path}/*.json.gz"):
        print(file)
        beatmap = DataFile(file)
        beatmap.load_data()
        beatmap = beatmap.data
        filemap = BinaryFile(file.replace(".json.gz", ".osu.gz"))
        if not filemap.exists():
            process_beatmap(beatmap)
        if not filemap.exists():
            logger.warn(f"skipping {beatmap['beatmap_id']}, probably deleted")
            continue
        if "attributes" not in beatmap:
            logger.warn(f"skipping {beatmap['beatmap_id']}, no attributes")
            continue
        tags = ""
        filemap.load_data()
        beatmap_raw = filemap.data.decode("utf-8")
        for line in beatmap_raw.split("\n"):
            if line.startswith("Tags:"):
                tags = ",".join(line[5:].split())
        beatmap["tags"] = tags
        beatmap["md5"] = hashlib.md5(filemap.data).hexdigest()
        insert_beatmap(database.conn.cursor(), beatmap)
    database.conn.commit()
