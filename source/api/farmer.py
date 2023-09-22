from api.utils import get_mods, Relax, HardRock, DoubleTime, Hidden, Easy
from api.beatmaps import load_beatmap, base_path, get_by_leaderboard
from typing import List, Tuple, Dict, TypedDict
from api.files import DataFile, exists
from api.objects import Score, Beatmap
from api.logging import get_logger
from config import config
import numpy
import glob
import json

logger = get_logger("api.farmer")


class MapRatios(TypedDict):
    speed_aim: float
    speed_aim_pp: float
    speed_notes: float
    circles_object: float
    density: float


class Model(TypedDict):
    min_sr: float
    max_sr: float
    matches: List[MapRatios]


class FutureBeatmap(TypedDict):
    matches: Dict[str, int]  # str: Model name, float: Match likelyhood
    most_likely: str  # Model name with the highest likelyhood
    beatmap_id: int
    pp_100: float
    pp_98: float
    pp_95: float
    mods: int


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

    scorefarmfile = DataFile(f"{config['common']['data_directory']}/score_farm.json.gz")
    if exists(f"{config['common']['data_directory']}/score_farm.json.gz"):
        scorefarmfile.load_data()
        scorefarm = scorefarmfile.data
        return

    beatmaps = []
    max_score = 0
    maps = get_by_leaderboard(
        columns=["beatmap_id", "length", "sliders", "circles", "spinners"],
        leaderboards=["akatsuki_ranked", "bancho_ranked"],
    )
    for id, length, sliders, circles, spinners in (
        maps["akatsuki_ranked"] + maps["bancho_ranked"]
    ):
        beatmap = {}
        beatmap["length"] = length
        beatmap["max_score"] = (sliders * 350) + (circles * 300) + (spinners * 1000)
        beatmap["beatmap_id"] = id
        beatmap["score_minute"] = beatmap["max_score"] / (beatmap["length"] / 60)
        max_score = max(beatmap["score_minute"], max_score)
        beatmaps.append(beatmap)
    beatmaps.sort(key=lambda x: x["score_minute"], reverse=True)
    result = [(beatmap, beatmap["score_minute"] / max_score) for beatmap in beatmaps]
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


class Recommendation(TypedDict):
    future: FutureBeatmap
    threshold: int
    match: str
    pp_avg: int


def recommend_next(
    pp_min,
    pp_max,
    samples=1,
    mods=None,
    mods_include=[],
    mods_exclude=[],
    skip_id=[],
    matches_threshold=0.85,
    matches_types=[],
) -> List[Recommendation]:
    possible_futures = []
    for future in futures:
        if future["beatmap_id"] in skip_id:
            continue
        future_mods = "".join(get_mods(future["mods"]))
        threshold = future["matches"][future["most_likely"]]
        match_name = future["most_likely"]
        avg_pp = (future["pp_98"] + future["pp_100"]) / 2
        if avg_pp < pp_min or avg_pp > pp_max:
            continue
        if mods:
            if future_mods != mods:
                continue
        fail = False
        if mods_include:
            for mod in mods_include:
                if mod not in future_mods:
                    fail = True
        if mods_exclude:
            for mod in mods_exclude:
                if mod in future_mods:
                    fail = True
        if fail:
            continue
        if matches_types:
            threshold = 0
            match_name = None
            for match_type in future["matches"]:
                if match_type.lower() in matches_types:
                    match_threshold = future["matches"][match_type]
                    if match_threshold > threshold:
                        match_name = match_type
                        threshold = match_threshold
            if not match_name:
                continue
        if threshold < matches_threshold:
            continue
        possible_futures.append(
            {
                "future": future,
                "match": match_name,
                "threshold": threshold,
                "pp_avg": avg_pp,
            }
        )
    if not possible_futures:
        return
    possible_futures.sort(
        key=lambda x: x["threshold"], reverse=True
    )  # maybe not needed?
    weights = [possible["threshold"] for possible in possible_futures]
    return random_choices(possible_futures, weights, samples)


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


futures: List[FutureBeatmap] = None
models: List[Tuple[str, str]] = []


def calculate_ratio(beatmap: Beatmap, mods: int) -> MapRatios:
    difficulty = beatmap["difficulty"][str(mods)]
    attributes = beatmap["attributes"]
    divisor = 1.5 if (mods & 64) else 1

    def ensure_value(value):
        return value if value else 1

    return MapRatios(
        speed_aim=ensure_value(difficulty["speed_rating"])
        / ensure_value(difficulty["aim_rating"]),
        speed_aim_pp=ensure_value(difficulty["speed_pp"])
        / ensure_value(difficulty["aim_pp"]),
        speed_notes=ensure_value(difficulty["speed_note_count"])
        / ensure_value(attributes["circles"]),
        circles_object=ensure_value(attributes["circles"])
        / ensure_value(attributes["sliders"])
        + attributes["spinners"],
        density=attributes["max_combo"] / (attributes["length"] / divisor),
    )


def compare_ratio(ratioA: MapRatios, ratioB: MapRatios):
    key_entries = len(ratioA.keys())
    likelyhood = 0.0

    def calc(n1, n2):
        return 1 - abs(n1 - n2) / (n1 + n2)

    for key in ratioA.keys():
        likelyhood += calc(ratioA[key], ratioB[key]) / key_entries
    return likelyhood


def check_against_model(ratio: MapRatios, model: Model):
    avg = 0.0
    best = 0.0
    for model_ratio in model["matches"]:
        likelyhood = compare_ratio(ratio, model_ratio)
        best = max(likelyhood, best)
        avg += likelyhood
    avg /= len(model["matches"])
    return best, avg


def build_model(min_sr, max_sr, beatmaps: List[Tuple[Beatmap, int]]) -> Model:
    return Model(
        min_sr=min_sr,
        max_sr=max_sr,
        matches=[calculate_ratio(beatmap, mods) for beatmap, mods in beatmaps],
    )


def process_models(models: Dict[str, Model]):
    futures = []
    for beatmap_file in glob.glob(f"{base_path}/*.json.gz"):
        try:
            id = beatmap_file.replace(f"{base_path}/", "").replace(".json.gz", "")
            beatmap = load_beatmap(int(id), difficulty_info=True)
            if (
                not beatmap
                or "attributes" not in beatmap
                or "difficulty" not in beatmap
                or "status" not in beatmap
            ):
                continue
            if beatmap["status"]["akatsuki"] < 1 or beatmap["status"]["akatsuki"] > 2:
                continue
            mods_combo = [
                Relax,
                HardRock,
                Relax + DoubleTime + Hidden,
                Relax + DoubleTime + Hidden + HardRock,
                Relax + DoubleTime + Hidden + Easy,
            ]
            for mods in mods_combo:
                difficulty = beatmap["difficulty"][str(mods)]
                ratio = calculate_ratio(beatmap, mods)
                matches = {}
                for model_name, model in models.items():
                    if difficulty["star_rating"] < model["min_sr"]:
                        continue
                    if difficulty["star_rating"] > model["max_sr"]:
                        continue
                    best, avg = check_against_model(ratio, model)
                    matches[model_name] = best
                    matches[f"{model_name}_avg"] = avg
                if not matches:
                    continue
                highest_match = ("", 0)
                lowest_match = ("", 10000000)
                for model_name, likely in matches.items():
                    if likely > highest_match[1]:
                        highest_match = (model_name, likely)
                    if likely < lowest_match[1]:
                        lowest_match = (model_name, likely)
                # logger.info(
                #     f"{beatmap['beatmap_id']}: Best match: {highest_match[0]} {highest_match[1]*100:.2f}% Worst match: {lowest_match[0]} {lowest_match[1]*100:.2f}%"
                # )
                futures.append(
                    FutureBeatmap(
                        beatmap_id=beatmap["beatmap_id"],
                        most_likely=highest_match[0],
                        pp_100=difficulty["pp_100"],
                        pp_98=difficulty["pp_98"],
                        pp_95=difficulty["pp_95"],
                        mods=mods,
                        matches=matches,
                    )
                )
        except Exception as e:
            if type(e) == ZeroDivisionError:  # incomplete data
                continue
            logger.warn(f"Skipping processing beatmap id {id}", exc_info=True)
    return futures


def load_models():
    models: Dict[str, Model] = {}
    for file in glob.glob(f"{config['common']['data_directory']}/farmer/*.json"):
        try:
            with open(file) as f:
                data = json.load(f)
            logger.info(f"Loading model {data['name']}")
            cache = DataFile(file + ".cache")
            if cache.exists():
                cache.load_data()
                models[data["name"]] = cache.data
            else:
                models[data["name"]] = build_model(
                    data["min_sr"],
                    data["max_sr"],
                    [
                        (
                            load_beatmap(entry["beatmap_id"], difficulty_info=True),
                            entry["mods"],
                        )
                        for entry in data["entries"]
                    ],
                )
                cache.data = models[data["name"]]
                cache.save_data()
        except:
            logger.warn(f"Could not load model {file}", exc_info=True)
            continue
    for model in models:
        logger.info("model name:" + model)
    return models


def load_farm():
    global futures, models
    futures_file = DataFile(
        f"{config['common']['data_directory']}/farmer/processed.json.gz"
    )
    for file in glob.glob(f"{config['common']['data_directory']}/farmer/*.json"):
        with open(file) as f:
            data = json.load(f)
        name = ""
        description = "No description."
        if "name" in data:
            name = data["name"]
        else:
            continue
        if "description" in data:
            description = data["description"]
        models.append((name, description))
    if not futures_file.exists():
        models = load_models()
        if not models:
            return
        futures_file.data = process_models(models)
        futures_file.save_data()
    else:
        futures_file.load_data()
    futures = futures_file.data


load_farm()
process_score_farm()
process_scores()
