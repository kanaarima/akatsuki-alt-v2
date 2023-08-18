from api.files import DataFile, exists
from api.objects import Beatmap
from config import config
from typing import List


base_path = f"{config['common']['data_directory']}/beatmaps"


def load_beatmap(beatmap_id) -> Beatmap:
    path = f"{base_path}/{beatmap_id}.json.gz"
    if not exists(path):
        return None
    file = DataFile(path)
    file.load_data()
    return file.data


def save_beatmap(beatmap: Beatmap, overwrite=False):
    path = f"{base_path}/{beatmap['beatmap_id']}.json.gz"
    if exists(path) and not overwrite:
        return
    file = DataFile(path)
    file.load_data()
    file.data = beatmap
    file.save_data()


def save_beatmaps(beatmaps: List[Beatmap], overwrite=False):
    for beatmap in beatmaps:
        save_beatmap(beatmap, overwrite)
