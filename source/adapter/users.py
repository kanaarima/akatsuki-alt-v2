import api.database as database
from api.files import DataFile
from config import config


def convert_users():
    file_links = DataFile(
        filepath=f"{config['common']['data_directory']}/users_statistics/users_discord.json.gz"
    )
    file_links.load_data()
    c = database.ConnectionHandler()
    for discord_id in file_links.data:
        data = file_links.data[discord_id]
        c.execute(
            "INSERT OR REPLACE INTO users VALUES(?,?,?,?,?,?)",
            (
                data[0]["id"],
                data[0]["clan_id"] if "clan_id" in data[0] else 0,
                data[0]["name"],
                data[0]["country"],
                discord_id,
                data[1],
            ),
        )
