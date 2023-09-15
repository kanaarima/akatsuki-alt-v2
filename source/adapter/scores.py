import api.database as db
from api.files import DataFile
from config import config
import glob
import time


def main():
    for file in glob.glob(
        f"{config['common']['data_directory']}/users_statistics/scores/*.json.gz"
    ):
        user_id = int(file.split("/")[-1].replace(".json.gz", ""))
        datafile = DataFile(file)
        datafile.load_data()
        for mode in datafile.data:
            for score in datafile.data[mode]:
                score = datafile.data[mode][score]
                print(
                    (
                        score["beatmap_id"],
                        mode,
                        score["id"],
                        user_id,
                        score["accuracy"],
                        score["mods"],
                        score["pp"],
                        score["score"],
                        score["combo"],
                        score["rank"],
                        score["count_300"],
                        score["count_100"],
                        score["count_50"],
                        score["count_miss"],
                        score["date"],
                    )
                )
                db.conn.execute(
                    "INSERT OR REPLACE INTO users_scores VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        score["beatmap_id"],
                        mode,
                        score["id"],
                        user_id,
                        score["accuracy"],
                        score["mods"],
                        score["pp"],
                        score["score"],
                        score["combo"],
                        score["rank"],
                        score["count_300"],
                        score["count_100"],
                        score["count_50"],
                        score["count_miss"],
                        score["date"],
                    ),
                )
