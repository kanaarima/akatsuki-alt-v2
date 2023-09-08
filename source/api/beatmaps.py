from api.objects import Beatmap, BeatmapAttributes, BeatmapDifficulty, RankedStatus
from api.files import DataFile, BinaryFile, exists
from akatsuki_pp_py import Beatmap as calc_beatmap
from akatsuki_pp_py import Calculator
from utils.api import DEFAULT_HEADERS
from api.akatsuki import get_map_info
from api.logging import get_logger
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


def load_beatmap(beatmap_id, force_fetch=False) -> Beatmap:
    global cache, cache_last_refresh
    if (datetime.now() - cache_last_refresh).total_seconds() > config["common"][
        "cache"
    ]:
        cache = {}
        cache_last_refresh = datetime.now()
    if beatmap_id in cache and cache_enabled:
        return cache[beatmap_id]
    path = f"{base_path}/{beatmap_id}.json.gz"
    new = None
    if not exists(path) or force_fetch:
        new = process_beatmap(beatmap=Beatmap(beatmap_id=beatmap_id))
        if len(new.keys()) == 1:
            return
        if cache_enabled:
            cache[beatmap_id] = new
    file = DataFile(path)
    file.load_data()
    if new:
        file.data = new
    if (
        "attributes" not in file.data
        or "difficulty" not in file.data
        and file.data["attributes"]["mode"] == 0
    ):
        file.data = {"beatmap_id": beatmap_id}
        process_beatmap(file.data)
    if cache_enabled:
        cache[beatmap_id] = file.data
    file.save_data()
    return file.data


def save_beatmap(beatmap: Beatmap, overwrite=False, trustable=False):
    global cache, cache_last_refresh
    path = f"{base_path}/{beatmap['beatmap_id']}.json.gz"
    if exists(path) and not overwrite:
        return
    if not trustable:
        process_beatmap(beatmap)
    if "raw_beatmap" in beatmap:
        del beatmap["raw_beatmap"]
    file = DataFile(path)
    file.load_data()
    file.data = beatmap
    file.save_data()
    if (datetime.now() - cache_last_refresh).total_seconds() > config["common"][
        "cache"
    ]:
        cache = {}
        cache_last_refresh = datetime.now()
    if cache_enabled:
        cache[beatmap["beatmap_id"]] = beatmap


def save_beatmaps(beatmaps: List[Beatmap], overwrite=False, trustable=False):
    for beatmap in beatmaps:
        save_beatmap(beatmap, overwrite, trustable)


def process_beatmap(beatmap: Beatmap) -> Beatmap:
    path = f"{base_path}/{beatmap['beatmap_id']}.osu.gz"
    if not exists(path):
        if not download_beatmap(beatmap["beatmap_id"]):
            logger.warn(f"Map {beatmap['beatmap_id']} can't be downloaded!")
            fix_metadata(beatmap)
            return beatmap
    try:
        fix_metadata(beatmap)
        file = BinaryFile(path)
        file.load_data()
        calc_map = calc_beatmap(bytes=file.data)
        if "attributes" in beatmap and beatmap["attributes"]["mode"] == 0:
            beatmap["difficulty"] = get_difficulties(calc_map)
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
    beatmap["difficulty_name"] = b.version
    beatmap["mapper"] = b._beatmapset.creator

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
