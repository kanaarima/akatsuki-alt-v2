from api.objects import LinkedPlayer
import api.akatsuki as akatsuki
from api.files import DataFile
from config import config
import front.bot as bot
import discord


async def handle_command(message: discord.Message):
    full = message.content[len(config["discord"]["bot_prefix"]) :]
    split = full.split(" ")
    if split[0] in commands:
        await commands[split[0]](full, split, message)
    else:
        await message.reply(content="Unknown command!")


async def ping(full: str, split: list[str], message: discord.Message):
    await message.reply(content="pong!")


async def link(full: str, split: list[str], message: discord.Message):
    if len(split) < 2:
        await message.reply(f"!link username/userID")
        return
    userid = -1
    if split[1].isnumeric():
        userid = int(split[1])
    else:
        userid = akatsuki.lookup_user(" ".join(split[1:]))
        if not userid:
            await message.reply(f"No user matching found. Perhaps use UserID?")
            return
    file_tracking = DataFile(
        filepath=f"{config['common']['data_directory']}/users_statistics/users.json.gz"
    )
    file_links = DataFile(
        filepath=f"{config['common']['data_directory']}/users_statistics/users_discord.json.gz"
    )
    file_tracking.load_data(default=list())
    file_links.load_data(default={})
    for user in file_tracking.data:
        if user["user_id"] == userid:
            user["full_tracking"] = True
        else:
            file_tracking.data.append(LinkedPlayer(user_id=userid, full_tracking=True))
    file_links.data[message.author.id] = userid
    file_tracking.save_data()
    file_links.save_data()
    await message.reply(f"Linked successfully.")


async def show_recent(full: str, split: list[str], message: discord.Message):
    pass


commands = {"ping": ping, "link": link}
