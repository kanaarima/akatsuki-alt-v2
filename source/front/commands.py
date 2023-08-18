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


async def ping(full, split, message: discord.Message):
    await message.reply(content="pong!")


commands = {"ping": ping}
