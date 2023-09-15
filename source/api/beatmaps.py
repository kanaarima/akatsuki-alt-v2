from api.objects import Beatmap, BeatmapAttributes, BeatmapDifficulty, RankedStatus
from api.files import BinaryFile, exists
from akatsuki_pp_py import Beatmap as calc_beatmap
from akatsuki_pp_py import Calculator
from utils.api import DEFAULT_HEADERS
from api.akatsuki import get_map_info
from api.logging import get_logger
from itertools import zip_longest
import api.database as database
from typing import List, Dict
from datetime import datetime
from config import config
import api.utils as utils
from time import sleep
import itertools
import requests
import ossapi

base_path = f"{config['common']['data_directory']}/beatmaps"
client = ossapi.Ossapi(
    client_id=config["osuapi"]["client_id"],
    client_secret=config["osuapi"]["client_secret"],
)
cache = {}
cache_last_refresh = datetime.now()
cache_enabled = False
logger = get_logger("api.beatmaps")


def _insert_beatmap(db, beatmap: Beatmap):
    query = """INSERT OR REPLACE INTO "main"."beatmaps" ("beatmap_id", "beatmap_set_id", "md5", "artist", "title", "difficulty_name", "mapper", "bancho_status", "akatsuki_status", "last_checked", "ar", "od", "cs", "length", "bpm", "max_combo", "circles", "sliders", "spinners", "mode", "tags", "stars_nm", "stars_ez", "stars_hr", "stars_dt", "stars_dtez", "stars_dthr") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?);"""
    query_nodiff = """INSERT OR REPLACE INTO "main"."beatmaps" ("beatmap_id", "beatmap_set_id", "md5", "artist", "title", "difficulty_name", "mapper", "bancho_status", "akatsuki_status", "last_checked", "ar", "od", "cs", "length", "bpm", "max_combo", "circles", "sliders", "spinners", "mode", "tags") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?, ?);"""
    last_checked = None
    if "status" not in beatmap:
        logger.warn(f"Dropping {beatmap['beatmap_id']}")
        return
    if "tags" not in beatmap:
        beatmap["tags"] = ""
    if "last_checked" in beatmap["status"]:
        last_checked = beatmap["status"]["last_checked"]
    else:
        last_checked = utils.datetime_to_str(datetime(year=1984, month=1, day=1))
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
        utils.non_null(beatmap["attributes"]["ar"]),
        utils.non_null(beatmap["attributes"]["od"]),
        utils.non_null(beatmap["attributes"]["cs"]),
        utils.non_null(beatmap["attributes"]["length"]),
        utils.non_null(beatmap["attributes"]["bpm"]),
        utils.non_null(beatmap["attributes"]["max_combo"]),
        utils.non_null(beatmap["attributes"]["circles"]),
        utils.non_null(beatmap["attributes"]["sliders"]),
        utils.non_null(beatmap["attributes"]["spinners"]),
        utils.non_null(beatmap["attributes"]["mode"]),
        beatmap["tags"],
    ]
    if "stars" in beatmap["attributes"]:
        args.append(beatmap["attributes"]["stars"][0])
        args.append(beatmap["attributes"]["stars"][utils.Easy])
        args.append(beatmap["attributes"]["stars"][utils.HardRock])
        args.append(beatmap["attributes"]["stars"][utils.DoubleTime])
        args.append(beatmap["attributes"]["stars"][utils.Easy + utils.DoubleTime])
        args.append(beatmap["attributes"]["stars"][utils.HardRock + utils.DoubleTime])
        db.execute(query, args)
    else:
        db.execute(query_nodiff, args)

    db.close()
    database.conn.commit()


def _get_beatmap(map):
    return Beatmap(
        beatmap_id=map[0],
        beatmap_set_id=map[1],
        md5=map[2],
        artist=map[3],
        title=map[4],
        difficulty_name=map[5],
        mapper=map[6],
        status=RankedStatus(bancho=map[7], akatsuki=map[8], last_checked=map[9]),
        attributes=BeatmapAttributes(
            ar=map[10],
            od=map[11],
            cs=map[12],
            length=map[13],
            bpm=map[14],
            max_combo=map[15],
            circles=map[16],
            sliders=map[17],
            spinners=map[18],
            mode=map[19],
            tags=map[20],
            stars={
                0: map[21],
                2: map[22],
                16: map[23],
                64: map[24],
                66: map[25],
                80: map[26],
            },
        ),
    )


def load_beatmap(beatmap_id, force_fetch=False, difficulty_info=False) -> Beatmap:
    if force_fetch:
        new = process_beatmap(beatmap=Beatmap(beatmap_id=beatmap_id))
        if len(new.keys()) == 1:
            return
        return new
    cur = database.conn.cursor()
    query = "SELECT * FROM beatmaps WHERE beatmap_id = ?"
    check = cur.execute(query, (beatmap_id,))
    map = check.fetchall()
    cur.close()
    if not map:
        new = process_beatmap(beatmap=Beatmap(beatmap_id=beatmap_id))
        _insert_beatmap(database.conn.cursor(), new)
        return new
    map = map[0]
    beatmap = _get_beatmap(map)
    if difficulty_info:
        process_beatmap(beatmap, skip_metadata=True)
    return beatmap


def save_beatmap(beatmap: Beatmap, overwrite=False, trustable=False):
    cur = database.conn.cursor()
    query = "select exists(select 1 from beatmaps where beatmap_id=? collate nocase) limit 1"
    check = cur.execute(query, (beatmap["beatmap_id"],)).fetchone()[0]
    cur.close()
    if check and not overwrite:
        return
    if not trustable:
        process_beatmap(beatmap)
    _insert_beatmap(database.conn.cursor(), beatmap)


def save_beatmaps(beatmaps: List[Beatmap], overwrite=False, trustable=False):
    for beatmap in beatmaps:
        save_beatmap(beatmap, overwrite, trustable)


def process_beatmap(beatmap: Beatmap, skip_metadata=False) -> Beatmap:
    path = f"{base_path}/{beatmap['beatmap_id']}.osu.gz"
    if not exists(path):
        if not download_beatmap(beatmap["beatmap_id"]):
            logger.warn(f"Map {beatmap['beatmap_id']} can't be downloaded!")
            if not skip_metadata:
                fix_metadata(beatmap)
            return beatmap
    try:
        file = BinaryFile(path)
        file.load_data()
        if not skip_metadata:
            fix_metadata(beatmap)
            beatmap_raw = file.data.decode("utf-8")
            for line in beatmap_raw.split("\n"):
                if line.startswith("Tags:"):
                    tags = ",".join(line[5:].split())
                    beatmap["tags"] = tags
                    break
        calc_map = calc_beatmap(bytes=file.data)
        if "attributes" in beatmap and beatmap["attributes"]["mode"] == 0:
            beatmap["difficulty"] = get_difficulties(calc_map)
            beatmap["attributes"]["stars"] = {}
            beatmap["attributes"]["stars"][0] = beatmap["difficulty"]["0"][
                "star_rating"
            ]
            beatmap["attributes"]["stars"][2] = beatmap["difficulty"]["2"][
                "star_rating"
            ]
            beatmap["attributes"]["stars"][16] = beatmap["difficulty"]["16"][
                "star_rating"
            ]
            beatmap["attributes"]["stars"][64] = beatmap["difficulty"]["64"][
                "star_rating"
            ]
            beatmap["attributes"]["stars"][66] = beatmap["difficulty"]["66"][
                "star_rating"
            ]
            beatmap["attributes"]["stars"][80] = beatmap["difficulty"]["80"][
                "star_rating"
            ]

    except Exception as e:
        logger.error("Error occurred while processing map!", exc_info=True)
    return beatmap


def download_beatmap(beatmap_id) -> bool:
    sleep(1.5)
    if content := _osudirect_download(beatmap_id):
        return content

    # Use old.ppy.sh as backup endpoint
    return _ppy_download(beatmap_id)


def _osudirect_download(beatmap_id) -> bool:
    response = requests.get(
        f"https://osu.direct/api/osu/{beatmap_id}",
        headers=DEFAULT_HEADERS,
    )
    if not response.ok:
        logger.warning(f"GET {response.url} {response.status_code}")
        logger.warning(f"{response.text}")
        return False
    logger.info(f"GET {response.url} {response.status_code}")
    file = BinaryFile(f"{base_path}/{beatmap_id}.osu.gz")
    file.data = response.content
    file.save_data()
    return True


def _ppy_download(beatmap_id) -> bool:
    response = requests.get(
        f"https://old.ppy.sh/osu/{beatmap_id}",
        headers=DEFAULT_HEADERS,
    )
    if not response.ok or not response.content:
        logger.warning(f"GET {response.url} {response.status_code}")
        logger.warning(f"{response.text}")
        return False
    logger.info(f"GET {response.url} {response.status_code}")
    file = BinaryFile(f"{base_path}/{beatmap_id}.osu.gz")
    file.data = response.content
    file.save_data()
    return True


def fix_metadata(beatmap: Beatmap):
    b = None
    if "raw_beatmap" in beatmap:
        b = beatmap["raw_beatmap"]
        del beatmap["raw_beatmap"]
    else:
        try:
            b = client.beatmap(beatmap_id=beatmap["beatmap_id"])
        except:
            logger.warn(f"Map {beatmap['beatmap_id']} not found on bancho!")
            return
    beatmap["artist"] = b._beatmapset.artist
    beatmap["title"] = b._beatmapset.title
    beatmap["beatmap_set_id"] = b._beatmapset.id
    beatmap["beatmap_id"] = b.id  # prolly not needed
    beatmap["md5"] = b.checksum
    beatmap["difficulty_name"] = b.version
    beatmap["mapper"] = b._beatmapset.creator
    beatmap["tags"] = ""
    if "attributes" in beatmap:
        beatmap["attributes"]["length"] = b.hit_length
    else:
        attributes = BeatmapAttributes()
        attrs = client.beatmap_attributes(beatmap_id=beatmap["beatmap_id"])
        attributes["length"] = b.hit_length
        attributes["ar"] = b.ar
        attributes["bpm"] = b.bpm
        attributes["circles"] = b.count_circles
        attributes["max_combo"] = b.max_combo
        attributes["sliders"] = b.count_sliders
        attributes["spinners"] = b.count_spinners
        attributes["od"] = attrs.attributes.overall_difficulty
        attributes["cs"] = b.cs
        attributes["mode"] = b.mode_int
        beatmap["attributes"] = attributes
    if "status" not in beatmap:
        beatmap["status"] = RankedStatus(
            bancho=b._beatmapset.ranked.value, akatsuki=b._beatmapset.ranked.value
        )
        if b._beatmapset.ranked.value < 1 or b._beatmapset.ranked.value > 2:
            if info := get_map_info(beatmap["beatmap_id"]):
                beatmap["status"]["akatsuki"] = (
                    info["ranked"] - 1
                )  # seems to be offset by 1
            beatmap["status"]["checked"] = utils.datetime_to_str(datetime.now())
    sleep(0.3)


# def get_attributes(beatmap: calc_beatmap) -> BeatmapAttributes:
#     attr = BeatmapAttributes()
#     calc = Calculator()
#     map_attrs = calc.map_attributes(beatmap)
#     attr["ar"] = map_attrs.ar
#     attr["cs"] = map_attrs.cs
#     attr["od"] = map_attrs.od
#     attr["bpm"] = map_attrs.bpm
#     attr["circles"] = map_attrs.n_circles
#     attr["sliders"] = map_attrs.n_sliders
#     attr["spinners"] = map_attrs.n_spinners
#     attr["mode"] = map_attrs.mode
#     attr["max_combo"] = map_attrs
#     map
#     return attr


def get_difficulty(beatmap: calc_beatmap, mods: int) -> BeatmapDifficulty:
    diff = BeatmapDifficulty()
    calc = Calculator(mods=mods)
    max_perf = calc.performance(beatmap)
    diff["pp_100"] = max_perf.pp
    diff["aim_pp"] = max_perf.pp_aim
    diff["speed_pp"] = max_perf.pp_speed
    diff["acc_pp"] = max_perf.pp_acc
    diff["aim_rating"] = max_perf.difficulty.aim
    diff["speed_rating"] = max_perf.difficulty.speed
    diff["star_rating"] = max_perf.difficulty.stars
    if mods & utils.Relax:
        new_calc = Calculator(mods=mods - utils.Relax)
        _max_perf = new_calc.performance(beatmap)
        diff["speed_note_count"] = int(_max_perf.difficulty.speed_note_count)
    else:
        diff["speed_note_count"] = int(max_perf.difficulty.speed_note_count)

    def set_diff(key, acc):
        calc.set_acc(acc)
        calc.set_difficulty(max_perf.difficulty)
        new_max_perf = calc.performance(beatmap)

        diff[key] = new_max_perf.pp

    set_diff("pp_99", 99)
    set_diff("pp_98", 98)
    set_diff("pp_97", 97)
    set_diff("pp_95", 95)
    set_diff("pp_90", 90)
    return diff


def get_difficulties(beatmap: calc_beatmap) -> Dict[int, BeatmapDifficulty]:
    res = {}
    time_mods = (0, utils.DoubleTime, utils.HalfTime)
    difficulty_mods = (0, utils.HardRock, utils.Easy)
    preference_mods_r = (utils.Hidden, utils.Flashlight)
    combinations = []
    for n in range(len(preference_mods_r) + 1):
        combinations += list(itertools.combinations(preference_mods_r, n))
    for time_mod, difficulty_mod in itertools.product(time_mods, difficulty_mods):
        for preference_mods in combinations:
            mods = sum(preference_mods) + difficulty_mod + time_mod
            res[str(mods)] = get_difficulty(beatmap, mods)
            res[str(mods + utils.Relax)] = get_difficulty(beatmap, mods + utils.Relax)
    return res


def get_by_leaderboard(leaderboards=[], columns="beatmap_id", mode=0):
    result = dict()
    queries = dict()
    queries[
        "ranked_bancho"
    ] = f"SELECT {columns} FROM beatmaps WHERE bancho_status BETWEEN 1 AND 2 AND mode = ?"
    queries[
        "loved_bancho"
    ] = f"SELECT {columns} FROM beatmaps WHERE bancho_status = 4 AND mode = ?"
    queries[
        "qualified_bancho"
    ] = f"SELECT {columns} FROM beatmaps WHERE bancho_status = 3 AND mode = ?"
    queries[
        "unranked"
    ] = f"SELECT {columns} FROM beatmaps WHERE akatsuki_status < 1 AND mode = ?"
    queries[
        "ranked_akatsuki"
    ] = f"SELECT {columns} FROM beatmaps WHERE bancho_status != 1 AND akatsuki_status = 1 AND mode = ?"
    queries[
        "loved_akatsuki"
    ] = f"SELECT {columns} FROM beatmaps WHERE bancho_status != 4 AND akatsuki_status = 4 AND mode = ?"

    for query in queries:
        if leaderboards and query not in leaderboards:
            continue
        result[query] = list()
        cur = database.conn.cursor()
        check = cur.execute(queries[query], (mode,))
        for map in check.fetchall():
            result[query] += map
        length = len(columns.split(","))
        if length != 1:
            old = result[query]
            result[query] = [
                item for item in zip_longest(*[iter(old)] * length, fillvalue="")
            ]
        cur.close()
    return result


def get_by_range(entry, min, max, leaderboards=[], mode=0):
    result = dict()
    queries = dict()
    queries[
        "ranked_bancho"
    ] = f"SELECT beatmap_id FROM beatmaps WHERE bancho_status BETWEEN 1 AND 2 AND {entry} BETWEEN ? AND ? AND mode = ?"
    queries[
        "loved_bancho"
    ] = f"SELECT beatmap_id FROM beatmaps WHERE bancho_status = 4 AND {entry} BETWEEN ? AND ? AND mode = ?"
    queries[
        "qualified_bancho"
    ] = f"SELECT beatmap_id FROM beatmaps WHERE bancho_status = 3 AND {entry} BETWEEN ? AND ? AND mode = ?"
    queries[
        "unranked"
    ] = f"SELECT beatmap_id FROM beatmaps WHERE akatsuki_status < 1 AND {entry} BETWEEN ? AND ? AND mode = ?"
    queries[
        "ranked_akatsuki"
    ] = f"SELECT beatmap_id FROM beatmaps WHERE bancho_status != 1 AND akatsuki_status = 1 AND {entry} BETWEEN ? AND ? AND mode = ?"
    queries[
        "loved_akatsuki"
    ] = f"SELECT beatmap_id FROM beatmaps WHERE bancho_status != 4 AND akatsuki_status = 4 AND {entry} BETWEEN ? AND ? AND mode = ?"
    for query in queries:
        if leaderboards and query not in leaderboards:
            continue
        result[query] = list()
        cur = database.conn.cursor()
        check = cur.execute(queries[query], [min, max, mode])
        for map in check.fetchall():
            result[query] += map
        cur.close()
    return result


def get_completion_cache(
    mode=0,
    leaderboards=["ranked_bancho", "ranked_akatsuki", "loved_bancho", "loved_akatsuki"],
):
    data = {
        "Completion": get_by_leaderboard(
            columns="beatmap_id,mapper,artist,tags",
            leaderboards=leaderboards,
            mode=mode,
        )
    }
    for leaderboard in leaderboards:
        data[leaderboard] = {"stars": {}, "ar": {}, "od": {}, "cs": {}}
        for x in range(0, 11):
            data[leaderboard]["stars"][x] = get_by_range(
                "stars_nm", x, x + 0.9, [leaderboard], mode=mode
            )[leaderboard]
            data[leaderboard]["ar"][x] = get_by_range(
                "ar", x, x + 0.9, [leaderboard], mode=mode
            )[leaderboard]
            data[leaderboard]["od"][x] = get_by_range(
                "od", x, x + 0.9, [leaderboard], mode=mode
            )[leaderboard]
            data[leaderboard]["cs"][x] = get_by_range(
                "cs", x, x + 0.9, [leaderboard], mode=mode
            )[leaderboard]

    def add(dict, key, value):
        if key in dict:
            dict[key].append(value)
        else:
            dict[key] = [value]

    def sort_dict(dikt, key, reverse):
        return dict(sorted(dikt.items(), key=key, reverse=reverse))

    for key in data["Completion"]:
        data[key]["mappers"] = {}
        data[key]["artists"] = {}
        data[key]["tags"] = {}
        data[key]["total"] = list()
        for beatmap_id, mapper, artist, tags in data["Completion"][key]:
            data[key]["total"].append(beatmap_id)
            for tag in tags.split(","):
                add(data[key]["tags"], tag, beatmap_id)
            add(data[key]["mappers"], mapper, beatmap_id)
            add(data[key]["artists"], artist, beatmap_id)
        data[key]["mappers"] = sort_dict(
            data[key]["mappers"], lambda x: len(x[1]), reverse=True
        )
        data[key]["artists"] = sort_dict(
            data[key]["artists"], lambda x: len(x[1]), reverse=True
        )
        data[key]["tags"] = sort_dict(
            data[key]["tags"], lambda x: len(x[1]), reverse=True
        )

    return data
