from api.beatmaps import base_path, process_beatmap
from api.files import BinaryFile, DataFile
from api.logging import get_logger
import api.database as database
from api.objects import Beatmap
from config import config
import hashlib
import glob
import os

logger = get_logger("api.adapter")


def non_null(val):
    return 0 if not val else val


def insert_beatmap(db, beatmap: Beatmap):
    query = """INSERT OR REPLACE INTO "main"."beatmaps" ("beatmap_id", "beatmap_set_id", "md5", "artist", "title", "difficulty_name", "mapper", "bancho_status", "akatsuki_status", "ar", "od", "cs", "length", "bpm", "max_combo", "circles", "sliders", "spinners", "mode", "tags") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
    args = (
        beatmap["beatmap_id"],
        beatmap["beatmap_set_id"],
        beatmap["md5"],
        beatmap["artist"],
        beatmap["title"],
        beatmap["difficulty_name"],
        beatmap["mapper"],
        beatmap["status"]["bancho"],
        beatmap["status"]["akatsuki"],
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
    )
    db.execute(query, args)
    db.close()


def main():
    for file in glob.glob(f"{base_path}/*.json.gz"):
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
