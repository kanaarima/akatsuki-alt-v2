from front.cmd import authorized
import discord


async def insert_beatmap(full: str, split: list[str], message: discord.Message):
    if not await authorized(message, auth_level=1):
        return
    await message.reply("pong")
