import api.database as db
from api.files import DataFile
from config import config
import glob


def main():
    for file in glob.glob(
        f"{config['common']['data_directory']}/users_statistics/playtime/*.json.gz"
    ):
        user_id = int(file.split("/")[-1].replace(".json.gz", ""))
        datafile = DataFile(file)
        datafile.load_data()
        for mode in datafile.data:
            db.conn.execute(
                "INSERT INTO users_playtime VALUES(?,?,?,?,?,?)",
                (
                    user_id,
                    mode,
                    datafile.data[mode]["submitted_plays"],
                    datafile.data[mode]["unsubmitted_plays"],
                    datafile.data[mode]["most_played"]
                    if "most_played" in datafile.data[mode]
                    else 0,  # very old usecase, only needed on dev env with outdated fetch
                    datafile.data[mode]["last_play_id"]
                    if "last_play_id" in datafile.data[mode]
                    else 0,
                ),
            )
