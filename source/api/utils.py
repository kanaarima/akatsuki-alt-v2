import datetime


def merge_dict(source: dict, target: dict) -> None:
    for key in source.keys():
        if key not in target:
            target[key] = source[key]


def update_dicts(a: dict, b: dict) -> None:
    merge_dict(a, b)
    merge_dict(b, a)


def find_unique(check_func, iterA, iterB):
    a = list()
    b = list()
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


def yesterday() -> datetime.datetime:
    return (datetime.datetime.today() - datetime.timedelta(days=1)).date()


def other_yesterday() -> datetime.datetime:
    return (datetime.datetime.today() - datetime.timedelta(days=2)).date()


def datetime_to_str(dt: datetime.datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def str_to_datetime(str) -> datetime.datetime:
    return datetime.datetime.strptime(str, "%d/%m/%Y %H:%M:%S")


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
Perfect = 16384


def get_mods(magic_number):
    mods = list()
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
    return new
