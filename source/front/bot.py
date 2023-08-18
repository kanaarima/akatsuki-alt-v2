from front import tasks, commands
from config import config
import discord


class Bot(discord.Client):
    async def on_ready(self):
        print(f"Logged on as {self.user}!")
        tasks.init_tasks()

    async def on_message(self, message: discord.Message):
        text = message.content
        if not text.startswith(config["discord"]["bot_prefix"]):
            return
        await commands.handle_command(message)


intents = discord.Intents.default()
intents.message_content = True
client = Bot(intents=intents)


def main():
    client.run(config["discord"]["bot_token"])
