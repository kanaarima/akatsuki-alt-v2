from api.beatmaps import base_path
from api.logging import get_logger
from api.files import BinaryFile
from api.objects import Beatmap
from typing import List
import datetime
import struct
import hashlib
import gzip
import io

logger = get_logger("api.collections")
OA_S_PER_DAY = 8.64e4
OA_EPOC = datetime.datetime(1899, 12, 30, 0, 0, 0, tzinfo=datetime.timezone.utc)


def OADoubleNow():
    return (
        datetime.datetime.now(datetime.timezone.utc) - OA_EPOC
    ).total_seconds() / OA_S_PER_DAY


def uleb128encode(n):
    assert n >= 0
    arr = []
    while True:
        b = n & 0x7F
        n >>= 7
        if n == 0:
            arr.append(b)
            return bytearray(arr)
        arr.append(0x80 | b)


def format_str(s):
    s = bytes(s, "utf-8")
    return uleb128encode(len(s)) + s


def get_md5(id):
    beatmap_raw = BinaryFile(f"{base_path}/{id}.osu.gz")
    if beatmap_raw.exists():
        beatmap_raw.load_data()
        return hashlib.md5(beatmap_raw.data).hexdigest()
    logger.warn(f"Could not calculate MD5 for beatmap ID {id}!")
    return hashlib.md5("something").hexdigest()


def generate_collection(beatmaps: List[Beatmap], collection_name, filename):
    temp_bytes = format_str("o!dm8")
    temp_bytes += struct.pack("d", OADoubleNow())
    temp_bytes += format_str("N/A")
    temp_bytes += struct.pack("i", 1)

    temp_bytes += format_str(collection_name)
    temp_bytes += struct.pack("i", -1)  # online ID
    temp_bytes += struct.pack("i", len(beatmaps))  # amount of beatmaps

    for beatmap in beatmaps:
        temp_bytes += struct.pack("i", beatmap["beatmap_id"])
        temp_bytes += struct.pack("i", beatmap["beatmap_set_id"])
        temp_bytes += format_str(beatmap["artist"])
        temp_bytes += format_str(beatmap["title"])
        temp_bytes += format_str(beatmap["difficulty_name"])
        temp_bytes += format_str(get_md5(beatmap["beatmap_id"]))
        temp_bytes += format_str("")
        mode = 0
        temp_bytes += struct.pack("b", mode)
        stars = 0
        temp_bytes += struct.pack("d", stars)

    temp_bytes += struct.pack("i", 0)
    temp_bytes += format_str("By Piotrekol")

    f = open(filename, "wb")
    f.write(format_str("o!dm8"))
    f.write(gzip.compress(temp_bytes))
    f.close()
