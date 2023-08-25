from front import tasks, cmd
from config import config
import discord


class Bot(discord.Client):
    async def on_ready(self):
        print(f"Logged on as {self.user}!")
        tasks.init_tasks()

    async def on_message(self, message: discord.Message):
        if message.author.id == self.user.id:
            return
        text = message.content
        if not text.startswith(config["discord"]["bot_prefix"]):
            return
        await cmd.handle_command(message)


intents = discord.Intents.default()
intents.message_content = True
client = Bot(intents=intents)


def main():
    client.run(config["discord"]["bot_token"])
