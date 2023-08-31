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
    result = list()
    result_file = DataFile(
        f"{config['common']['data_directory']}/scores_processed.json.gz"
    )
    for id in average_pp.keys():
        for mods in average_pp[id].keys():
            if not average_pp[id][mods]:
                continue
            result.append(
                {
                    "beatmap_id": id,
                    "mods": mods,
                    "frequency_all": frequency[id],
                    "frequency_mods": frequency_mods[id][mods],
                    "average_pp": average_pp[id][mods],
                }
            )
    result_file.data = result
    result_file.save_data()


def recommend(pp_min, pp_max, samples=1, skip_id=[]):
    scores = DataFile(f"{config['common']['data_directory']}/scores_processed.json.gz")
    scores.load_data()
    freq_all_cap = 300
    freq_mods_cap = 100

    def get_weight(score):
        return ((min(score["frequency_all"], freq_all_cap) / freq_all_cap) / 2) + (
            (min(score["frequency_mods"], freq_mods_cap) / freq_mods_cap) / 2
        )

    found = list()
    weights = list()
    for score in scores.data:
        if score["beatmap_id"] in skip_id:
            continue
        pp = score["average_pp"]
        if pp < pp_min or pp > pp_max:
            continue
        weight = get_weight(score)
        score["weight"] = weight
        found.append(score)
        weights.append(weight)
    return random_choices(found, weights, samples)


def random_choices(data, weights, samples):
    normalised = numpy.asarray(weights)
    normalised /= normalised.sum()
    choices = numpy.random.choice(data, p=normalised, size=samples * 2)
    result = list()
    [result.append(x) for x in choices if x not in result]
    return result[:samples]
