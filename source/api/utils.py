from api.logging import get_logger
import api.objects as objects
import datetime
import time

logger = get_logger("utils")


def merge_dict(source: dict, target: dict) -> None:
    for key in source:
        if key not in target:
            target[key] = source[key]


def update_dicts(a: dict, b: dict) -> None:
    merge_dict(a, b)
    merge_dict(b, a)


def find_unique(check_func, iterA, iterB):
    a = []
    b = []
    for x in iterA:
        for y in iterB:
            if check_func(x, y):
                break
        else:
            a.append(x)
    for x in iterB:
        for y in iterA:
            if check_func(x, y):
                break
        else:
            b.append(x)
    return (a, b)


def today() -> datetime.datetime:
    return (datetime.datetime.now() - datetime.timedelta(days=1)).date()


def yesterday() -> datetime.datetime:
    return (datetime.datetime.now() - datetime.timedelta(days=1)).date()


def other_yesterday() -> datetime.datetime:
    return (datetime.datetime.now() - datetime.timedelta(days=2)).date()


def datetime_to_str(dt: datetime.datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def str_to_datetime(str) -> datetime.datetime:
    return datetime.datetime.strptime(str, "%d/%m/%Y %H:%M:%S")


def score_from_db(rows):
    return objects.Score(
        beatmap_id=rows[0],
        id=rows[2],
        accuracy=rows[4],
        mods=rows[5],
        pp=rows[6],
        score=rows[7],
        combo=rows[8],
        rank=rows[9],
        count_300=rows[10],
        count_100=rows[11],
        count_50=rows[12],
        count_miss=rows[13],
        date=rows[14],
    )


NoMod = 0
NoFail = 1
Easy = 2
TouchDevice = 4
Hidden = 8
HardRock = 16
SuddenDeath = 32
DoubleTime = 64
Relax = 128
HalfTime = 256
Nightcore = 512
Flashlight = 1024
SpunOut = 4096
AutoPilot = 8192
Perfect = 16384


def get_mods(magic_number):
    mods = []
    if magic_number & SpunOut:
        mods.append("SO")
    if magic_number & Easy:
        mods.append("EZ")
    if magic_number & Nightcore:
        mods.append("NC")
    if magic_number & HalfTime:
        mods.append("HT")
    if magic_number & Hidden:
        mods.append("HD")
    if magic_number & DoubleTime:
        mods.append("DT")
    if magic_number & HardRock:
        mods.append("HR")
    if magic_number & Flashlight:
        mods.append("FL")
    if magic_number & TouchDevice:
        mods.append("TD")
    if magic_number & SuddenDeath:
        mods.append("SD")
    if magic_number & NoFail:
        mods.append("NF")
    if magic_number & Perfect:
        mods.append("PF")
    if magic_number & Relax:
        mods.append("RX")
    return mods


def mods_from_string(mods_str):
    mods_str = mods_str.upper()
    if not mods_str or mods_str == "NM":
        return 0
    mods = 0
    if "NF" in mods_str:
        mods += NoFail
    if "EZ" in mods_str:
        mods += Easy
    if "TD" in mods_str:
        mods += TouchDevice
    if "HD" in mods_str:
        mods += Hidden
    if "HR" in mods_str:
        mods += HardRock
    if "SD" in mods_str:
        mods += SuddenDeath
    if "DT" in mods_str:
        mods += DoubleTime
    if "RX" in mods_str:
        mods += Relax
    if "HT" in mods_str:
        mods += HalfTime
    if "NC" in mods_str:
        mods += Nightcore
    if "FL" in mods_str:
        mods += Flashlight
    if "SO" in mods_str:
        mods += SpunOut
    if "AP" in mods_str:
        mods += AutoPilot
    if "PF" in mods_str:
        mods += Perfect
    return mods


def get_mods_simple(magic_number):
    mods = get_mods(magic_number)
    if "NC" in mods:
        mods.remove("DT")
    if "PF" in mods:
        mods.remove("SD")
    return mods


def convert_mods(magic_number):
    new = magic_number
    if magic_number & Nightcore:
        new -= Nightcore
    if magic_number & SpunOut:
        new -= SpunOut
    if magic_number & SuddenDeath:
        new -= SuddenDeath
    if magic_number & NoFail:
        new -= NoFail
    if magic_number & TouchDevice:
        new -= TouchDevice
    if magic_number & Perfect:
        new -= Perfect
    if magic_number & AutoPilot:
        new -= AutoPilot
    return new


def non_null(val):
    return 0 if not val else val


def calculate_max_score(attributes: objects.BeatmapAttributes):
    return (
        (attributes["circles"] * 300)
        + (attributes["sliders"] * 350)
        + (attributes["spinners"] * 1000)
    )


def execute(conn, query, args=None, timeout=100):
    elapsed = time.time()
    while True:
        try:
            if args:
                logger.debug(f"{type(query)} {type(args)}")
                return conn.execute(query, args)
            else:
                return conn.execute(query)
        except Exception as e:
            logger.warn(
                f"Got exception {type(e)} running query {query} with args {args}! retrying...",
                exc_info=True,
            )
            if time.time() - elapsed > timeout:
                break
            time.sleep(0.2)
