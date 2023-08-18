from api.objects import Player, Score
from api.beatmaps import load_beatmap
from api.utils import get_mods_simple
from typing import List
import discord


class ScoresView(discord.ui.View):
    def __init__(self, title: str, scores: List[Score], message=None):
        self.title = title
        self.scores = scores
        self.message = message
        self.index = 0
        super().__init__(timeout=180)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = max(0, self.index - 1)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = min(int(len(self.scores) / 10), self.index + 1)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def reply(self, message: discord.Message):
        self.message = await message.reply(embed=self.get_embed(), view=self)

    def get_embed(self):
        embed = discord.Embed(title=self.title)
        i = self.index * 10
        for score in self.scores[i : i + 10]:
            beatmap_info = load_beatmap(score["beatmap_id"])
            if not beatmap_info:
                text += "Unknown Beatmap?\n"
                continue
            text_beatmap = f"{beatmap_info['artist']} - {beatmap_info['title']} [{beatmap_info['difficulty']}]"
            text_score = f"mods: {''.join(get_mods_simple(score['mods']))} "
            text_score += f"300/100/50/X: {score['count_300']}/{score['count_100']}/{score['count_50']}/{score['count_miss']} "
            text_score += f"Accuracy: {score['accuracy']:.2f}%\n "
            text_score += f"Rank: {score['rank']} "
            text_score += f"Combo: {score['combo']}x "
            text_score += f"Score: {score['score']:,} "
            text_score += f"PP: {score['pp']}pp\n"
            embed.add_field(name=text_beatmap, value=text_score, inline=False)
        return embed
