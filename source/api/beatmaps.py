from api.objects import Beatmap, BeatmapAttributes, BeatmapDifficulty, RankedStatus
from api.files import DataFile, BinaryFile, exists
from akatsuki_pp_py import Beatmap as calc_beatmap
from akatsuki_pp_py import Calculator
from utils.api import DEFAULT_HEADERS
from typing import List, Dict
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


def load_beatmap(beatmap_id) -> Beatmap:
    path = f"{base_path}/{beatmap_id}.json.gz"
    if not exists(path):
        new = process_beatmap(beatmap=Beatmap(beatmap_id=beatmap_id))
        if len(new.keys()) == 1:
            return
        return new
    file = DataFile(path)
    file.load_data()
    return file.data


def save_beatmap(beatmap: Beatmap, overwrite=False, trustable=False):
    path = f"{base_path}/{beatmap['beatmap_id']}.json.gz"
    if exists(path) and not overwrite:
        return
    if not trustable:
        process_beatmap(beatmap)
    file = DataFile(path)
    file.load_data()
    file.data = beatmap
    file.save_data()


def save_beatmaps(beatmaps: List[Beatmap], overwrite=False, trustable=False):
    for beatmap in beatmaps:
        save_beatmap(beatmap, overwrite, trustable)


def process_beatmap(beatmap: Beatmap) -> Beatmap:
    path = f"{base_path}/{beatmap['beatmap_id']}.osu.gz"
    if not exists(path):
        if not download_beatmap(beatmap["beatmap_id"]):  # Mirror has no map
            return beatmap
    try:
        file = BinaryFile(path)
        file.load_data()
        calc_map = calc_beatmap(bytes=file.data)
        fix_metadata(beatmap)
        if "attributes" in beatmap and beatmap["attributes"]["mode"] == 0:
            beatmap["difficulty"] = get_difficulties(calc_map)
    except Exception as e:
        raise e
        print(e)  # TODO
    return beatmap


def download_beatmap(beatmap_id) -> True:
    sleep(1.5)
    return _osudirect_download(beatmap_id)


def _osudirect_download(beatmap_id) -> True:
    req = requests.get(
        f"https://osu.direct/api/osu/{beatmap_id}",
        headers=DEFAULT_HEADERS,
    )
    if req.status_code != 200:
        return False
    file = BinaryFile(f"{base_path}/{beatmap_id}.osu.gz")
    file.data = req.content
    file.save_data()
    return True


def fix_metadata(beatmap: Beatmap):
    b = None
    try:
        b = client.beatmap(beatmap_id=beatmap["beatmap_id"])
    except:
        print(f"Couldn't find {beatmap}")
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
    combinations = list()
    for n in range(len(preference_mods_r) + 1):
        combinations += list(itertools.combinations(preference_mods_r, n))
    for time_mod in time_mods:
        for difficulty_mod in difficulty_mods:
            for preference_mods in combinations:
                mods = sum(preference_mods) + difficulty_mod + time_mod
                res[str(mods)] = get_difficulty(beatmap, mods)
                res[str(mods + utils.Relax)] = get_difficulty(
                    beatmap, mods + utils.Relax
                )
    return res
