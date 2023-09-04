from api.files import DataFile, exists
from api.utils import get_mods
from api.objects import Score
from config import config
from typing import List
import numpy


def process_scores():
    path = f"{config['common']['data_directory']}/scores.json.gz"
    if not exists(path):
        return
    result = []
    result_file = DataFile(
        f"{config['common']['data_directory']}/scores_processed.json.gz"
    )
    if result_file.exists():
        return
    file = DataFile(path)
    file.load_data()
    scores: List[Score] = file.data
    frequency = {}
    frequency_mods = {}
    average_pp = {}
    to_delete = ["NF", "SO", "PF", "SD", "NC"]
    for score in scores:
        beatmap_id = score["beatmap_id"]
        mods = get_mods(score["mods"])
        for mod in to_delete:
            if mod in mods:
                mods.remove(mod)
        mods = "".join(mods)
        if beatmap_id not in frequency:
            frequency[beatmap_id] = 1
        else:
            frequency[beatmap_id] += 1
        if beatmap_id not in frequency_mods:
            frequency_mods[beatmap_id] = {}
            average_pp[beatmap_id] = {}
        if mods not in frequency_mods[beatmap_id]:
            frequency_mods[beatmap_id][mods] = 1
            average_pp[beatmap_id][mods] = None
        else:
            frequency_mods[beatmap_id][mods] += 1
        if score["count_miss"] > 5 or score["accuracy"] < 97:
            continue
        if not average_pp[beatmap_id][mods]:
            average_pp[beatmap_id][mods] = score["pp"]
        else:
            average_pp[beatmap_id][mods] = (
                score["pp"] + average_pp[beatmap_id][mods]
            ) / 2

    for id, value in average_pp.items():
        result.extend(
            {
                "beatmap_id": id,
                "mods": mods,
                "frequency_all": frequency[id],
                "frequency_mods": frequency_mods[id][mods],
                "average_pp": average_pp[id][mods],
            }
            for mods in value.keys()
            if average_pp[id][mods]
        )
    result_file.data = result
    result_file.save_data()


scorefarm = None


def process_score_farm():
    global scorefarm
    if not exists(f"{config['common']['data_directory']}/beatmap_cache.json.gz"):
        return
    scorefarmfile = DataFile(f"{config['common']['data_directory']}/score_farm.json.gz")
    if exists(f"{config['common']['data_directory']}/score_farm.json.gz"):
        scorefarmfile.load_data()
        scorefarm = scorefarmfile.data
        return

    cache = DataFile(f"{config['common']['data_directory']}/beatmap_cache.json.gz")
    cache.load_data()
    beatmaps = []
    max_score = 0
    for id in cache.data["metadata"].keys():
        if (
            int(id) not in cache.data["ranked"]["total"]
            and int(id) not in cache.data["ranked_akatsuki"]["total"]
        ):
            continue
        beatmap = cache.data["metadata"][id]
        if not beatmap["length"]:
            continue
        beatmap["beatmap_id"] = id
        beatmap["score_minute"] = beatmap["max_score"] / (beatmap["length"] / 60)
        max_score = max(beatmap["score_minute"], max_score)
        beatmaps.append(beatmap)
    beatmaps.sort(key=lambda x: x["score_minute"], reverse=True)
    result = [
        (beatmap, beatmap["score_minute"] / max_score) for beatmap in beatmaps
    ]
    scorefarmfile.data = result
    scorefarmfile.save_data()
    scorefarm = result


def recommend(
    pp_min,
    pp_max,
    samples=1,
    mods=None,
    mods_include=[],
    mods_exclude=[],
    skip_id=[],
):
    scores = DataFile(f"{config['common']['data_directory']}/scores_processed.json.gz")
    scores.load_data()
    freq_all_cap = 300
    freq_mods_cap = 100

    def get_weight(score):
        return ((min(score["frequency_all"], freq_all_cap) / freq_all_cap) / 2) + (
            (min(score["frequency_mods"], freq_mods_cap) / freq_mods_cap) / 2
        )

    found = []
    weights = []
    for score in scores.data:
        if score["beatmap_id"] in skip_id:
            continue
        score_mods = [score["mods"][i : i + 2] for i in range(0, len(score["mods"]), 2)]
        failed = False
        for mod in mods_include:
            if mod not in score_mods:
                failed = True
        for mod in mods_exclude:
            if mod in score_mods:
                failed = True
        if mods:
            if "RX" not in mods:
                mods = f"{mods}RX"
            if mods != score["mods"]:
                failed = True
        if failed:
            continue
        pp = score["average_pp"]
        if pp < pp_min or pp > pp_max:
            continue
        weight = get_weight(score)
        score["weight"] = weight
        found.append(score)
        weights.append(weight)
    return random_choices(found, weights, samples)


def recommend_score(skip_id=[], samples=1):
    beatmaps = []
    weights = []
    max_maps = max(samples, 25)
    for beatmap, weight in scorefarm:
        if beatmap["beatmap_id"] in skip_id:
            continue
        beatmaps.append(beatmap)
        weights.append(weight)
        if len(beatmaps) == max_maps:
            break
    return random_choices(beatmaps, weights, samples)


def random_choices(data, weights, samples):
    normalised = numpy.asarray(weights)
    normalised /= normalised.sum()
    choices = numpy.random.choice(data, p=normalised, size=samples * 2)
    result = []
    [result.append(x) for x in choices if x not in result]
    return result[:samples]


process_score_farm()
process_scores()
