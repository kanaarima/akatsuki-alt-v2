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
    files = DataFile(
        filepath=f"{config['common']['data_directory']}/user_statistics/users.json.gz"
    )
    files.load_data(default=list())
    for user in files.data:
        if user["user_id"] == userid:
            user["full_tracking"] = True
        else:
            files.data.append(LinkedPlayer(user_id=userid, full_tracking=True))
    await message.reply(f"Linked successfully.")


commands = {"ping": ping, "link": link}
