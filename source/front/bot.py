from config import config
import discord


class Bot(discord.Client):
    async def on_ready(self):
        print(f"Logged on as {self.user}!")


intents = discord.Intents.default()
intents.message_content = True
client = Bot(intents=intents)


def main():
    client.run(config["discord"]["bot_token"])
