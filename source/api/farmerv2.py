from api.farmer import MapRatios, FutureBeatmap, calculate_ratio
import api.farmer as farmer
import api.database as database
import api.beatmaps as beatmaps
import api.utils as utils
from config import config
import itertools
import sqlite3

farmer_db = sqlite3.connect(
    config["database_farmer"], isolation_level=None, check_same_thread=False
)
models_full = farmer.load_models()

table_beatmap_query = """CREATE TABLE "beatmaps" (
	"beatmap_id"	INTEGER NOT NULL,
	"beatmap_name"	TEXT NOT NULL,
	"server"	TEXT NOT NULL,
	"ar"	REAL NOT NULL,
	"od"	REAL NOT NULL,
	"cs"	REAL NOT NULL,
	"stars_nm"	REAL NOT NULL,
	"stars_ez"	REAL,
	"stars_hr"	REAL,
	"stars_dt"	REAL NOT NULL,
	"stars_dtez"	REAL NOT NULL,
	"stars_dthr"	REAL NOT NULL,
	PRIMARY KEY("beatmap_id","server")
)"""

table_beatmap_difficulty_query = """CREATE TABLE "beatmaps_difficulty" (
	"beatmap_id"	INTEGER NOT NULL,
	"mode"	INTEGER NOT NULL,
	"mods"	INTEGER NOT NULL,
	"pp_100"	REAL NOT NULL,
	"pp_98"	REAL NOT NULL,
	"pp_95"	REAL NOT NULL,
	"speed_aim"	REAL NOT NULL,
	"speed_aim_pp"	REAL NOT NULL,
	"speed_notes"	REAL NOT NULL,
	"circles_object"	REAL NOT NULL,
	"density"	REAL NOT NULL,
	PRIMARY KEY("beatmap_id","mode","mods")
)"""


def load_beatmaps():
    maps = beatmaps.get_by_leaderboard(
        leaderboards=["ranked_bancho", "ranked_akatsuki"]
    )
    for map in maps["ranked_bancho"]:
        beatmap = beatmaps.load_beatmap(map)
        if "attributes" not in beatmap:
            continue
        title = (
            f"{beatmap['artist']} - {beatmap['title']} [{beatmap['difficulty_name']}]"
        )
        farmer_db.execute(
            f"INSERT OR IGNORE into beatmaps VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                beatmap["beatmap_id"],
                title,
                "bancho",
                beatmap["attributes"]["ar"],
                beatmap["attributes"]["od"],
                beatmap["attributes"]["cs"],
                beatmap["attributes"]["stars"][0],
                beatmap["attributes"]["stars"][2],
                beatmap["attributes"]["stars"][16],
                beatmap["attributes"]["stars"][64],
                beatmap["attributes"]["stars"][66],
                beatmap["attributes"]["stars"][80],
            ),
        )
    for map in maps["ranked_akatsuki"]:
        beatmap = beatmaps.load_beatmap(map)
        if "attributes" not in beatmap:
            continue
        title = (
            f"{beatmap['artist']} - {beatmap['title']} [{beatmap['difficulty_name']}]"
        )
        farmer_db.execute(
            f"INSERT OR IGNORE into beatmaps VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                beatmap["beatmap_id"],
                title,
                "akatsuki",
                beatmap["attributes"]["ar"],
                beatmap["attributes"]["od"],
                beatmap["attributes"]["cs"],
                beatmap["attributes"]["stars"][0],
                beatmap["attributes"]["stars"][2],
                beatmap["attributes"]["stars"][16],
                beatmap["attributes"]["stars"][64],
                beatmap["attributes"]["stars"][66],
                beatmap["attributes"]["stars"][80],
            ),
        )
    farmer_db.commit()


def calculate_ratios():
    for beatmap_id in farmer_db.execute("SELECT beatmap_id FROM beatmaps").fetchall():
        beatmap_id = beatmap_id[0]
        beatmap = beatmaps.load_beatmap(beatmap_id, difficulty_info=True)
        if not beatmap or "difficulty" not in beatmap:
            continue
        time_mods = (0, utils.DoubleTime, utils.HalfTime)
        difficulty_mods = (0, utils.HardRock, utils.Easy)
        preference_mods_r = (utils.Hidden, utils.Flashlight)
        combinations = []
        for n in range(len(preference_mods_r) + 1):
            combinations += list(itertools.combinations(preference_mods_r, n))
        for time_mod, difficulty_mod in itertools.product(time_mods, difficulty_mods):
            for preference_mods in combinations:
                mods = sum(preference_mods) + difficulty_mod + time_mod
                for modetype in [0, utils.Relax, utils.AutoPilot]:
                    ratio = calculate_ratio(beatmap, mods + modetype)
                    farmer_db.execute(
                        "INSERT OR REPLACE into beatmaps_difficulty VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            beatmap["beatmap_id"],
                            beatmap["attributes"]["mode"],
                            mods + modetype,
                            beatmap["difficulty"][str(mods + modetype)]["pp_100"],
                            beatmap["difficulty"][str(mods + modetype)]["pp_98"],
                            beatmap["difficulty"][str(mods + modetype)]["pp_95"],
                            ratio["speed_aim"],
                            ratio["speed_aim_pp"],
                            ratio["speed_notes"],
                            ratio["circles_object"],
                            ratio["density"],
                        ),
                    )
    farmer_db.commit()


def setup_db():
    farmer_db.execute("")
    if not database.table_exists("beatmaps", farmer_db):
        farmer_db.execute(table_beatmap_query)
        load_beatmaps()
    if not database.table_exists("beatmaps_difficulty", farmer_db):
        farmer_db.execute(table_beatmap_difficulty_query)
        calculate_ratios()
    farmer_db.execute("PRAGMA journal_mode=WAL;")
    farmer_db.execute("PRAGMA synchronous=normal;")
    farmer_db.execute("PRAGMA busy_timeout = 30000")
    farmer_db.commit()


setup_db()


def recommend_next(
    pp_min,
    pp_max,
    models=[],
    skip_id=[],
    mods=None,
    mods_include=None,
    mods_exclude=None,
    servers=["bancho"],
    threshold=0.85,
    samples=1,
):
    allowed_ids = list()
    possible_beatmaps = list()
    found_models = []
    for model in models:
        for loaded_models in farmer.models:
            if loaded_models[0].lower() == model.lower():
                if loaded_models[0] not in models_full:
                    continue
                found_models.append(models_full[loaded_models[0]])
    for server in servers:
        allowed_ids.extend(
            [
                rows[0]
                for rows in farmer_db.execute(
                    "SELECT beatmap_id FROM beatmaps WHERE server = ?", (server,)
                ).fetchall()
            ]
        )
    possible_beatmaps = farmer_db.execute(
        "SELECT * FROM beatmaps_difficulty WHERE pp_98 BETWEEN ? AND ?",
        (pp_min, pp_max),
    ).fetchall()
    to_remove = list()
    for possible_beatmap in possible_beatmaps:
        if possible_beatmap[0] not in allowed_ids:
            to_remove.append(possible_beatmap)
    for remove in to_remove:
        possible_beatmaps.remove(remove)
    futures = list()
    for possible_beatmap in possible_beatmaps:
        if skip_id and possible_beatmap[0] in skip_id:
            continue
        if mods:
            if possible_beatmap[2] != mods:
                continue
        beatmap_mods = utils.get_mods_simple(possible_beatmap[2])
        if mods_include:
            for to_include in mods_include:
                if to_include not in beatmap_mods:
                    continue
        if mods_exclude:
            for to_exclude in mods_exclude:
                if to_exclude in beatmap_mods:
                    continue
        ratio = MapRatios(
            speed_aim=possible_beatmap[6],
            speed_aim_pp=possible_beatmap[7],
            speed_notes=possible_beatmap[8],
            circles_object=possible_beatmap[9],
            density=possible_beatmap[10],
        )
        highest_match = 0
        for model in loaded_models:
            best, avg = farmer.check_against_model(ratio, model)
            if best > highest_match:
                highest_match = best
            if avg > highest_match:
                highest_match = avg
        if highest_match < threshold:
            continue
        # TODO include list of all matches
        avg_pp = (possible_beatmap[4] + possible_beatmap[3]) / 2
        futures.append(
            {
                "future": FutureBeatmap(
                    matches={"avg": highest_match},
                    most_likely="avg",
                    beatmap_id=possible_beatmap[0],
                    pp_100=possible_beatmap[3],
                    pp_98=possible_beatmap[4],
                    pp_95=possible_beatmap[5],
                    mods=possible_beatmap[2],
                ),
                "match": "avg",
                "threshold": highest_match,
                "pp_avg": avg_pp,
            }
        )
    if not futures:
        return
    futures.sort(key=lambda x: x["threshold"], reverse=True)  # maybe not needed?
    weights = [possible["threshold"] for possible in futures]
    return farmer.random_choices(futures, weights, samples)
