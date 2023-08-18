from discord.ext import tasks
import front.bot as bot
import discord


@tasks.loop(seconds=60)
async def post_lb_updates():
    pass


def init_tasks():
    post_lb_updates.start()
