from discord.ext import tasks
import discord

client: discord.Client = None


@tasks.loop(seconds=60)
async def post_lb_updates():
    pass


def init_tasks(_client: discord.Client):
    global client
    client = _client
    post_lb_updates.start()
