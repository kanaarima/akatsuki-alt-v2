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
            text_beatmap = f"{beatmap_info['artist']} - {beatmap_info['title']} [{beatmap_info['difficulty_name']}]"
            text_score = f"mods: {''.join(get_mods_simple(score['mods']))} "
            text_score += f"300/100/50/X: {score['count_300']}/{score['count_100']}/{score['count_50']}/{score['count_miss']} "
            text_score += f"Accuracy: {score['accuracy']:.2f}%\n "
            text_score += f"Rank: {score['rank']} "
            text_score += f"Combo: {score['combo']}x "
            text_score += f"Score: {score['score']:,} "
            text_score += f"PP: {score['pp']}pp\n"
            embed.add_field(name=text_beatmap, value=text_score, inline=False)
        return embed


class ScoreDiffView(discord.ui.View):
    def __init__(
        self, title: str, scores_old: List[Score], scores_new: List[Score], message=None
    ):
        self.title = title
        self.message = message
        self.index = 0
        self.status = 0
        self.scores_lost = list()
        self.scores_gained = scores_new.copy()
        self.scores_overwritten = list()
        for score in scores_old:
            found = False
            for score_new in scores_new:
                if score["id"] == score_new["id"]:
                    self.scores_gained.remove(score_new)
                    found = True
                    break
                if score["beatmap_id"] == score_new["beatmap_id"]:
                    found = True
                    self.scores_gained.remove(score_new)
                    self.scores_overwritten.append(score_new)
                    break
            if not found:
                self.scores_lost.append(score)
        self.scores = self.scores_gained
        super().__init__(timeout=180)

    labels = ["new", "lost", "overwritten"]

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = max(0, self.index - 1)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = min(int(len(self.scores) / 10), self.index + 1)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Current: new", style=discord.ButtonStyle.gray)
    async def typebutton(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.index = 0
        self.status += 1
        if self.status > 2:
            self.status = 0
        self.scores = self.scores_gained
        if self.status == 1:
            self.scores = self.scores_lost
        elif self.status == 2:
            self.scores = self.scores_overwritten
        button.label = f"Current: {self.labels[self.status]}"
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
            text_beatmap = f"{beatmap_info['artist']} - {beatmap_info['title']} [{beatmap_info['difficulty_name']}]"
            text_score = f"mods: {''.join(get_mods_simple(score['mods']))} "
            text_score += f"300/100/50/X: {score['count_300']}/{score['count_100']}/{score['count_50']}/{score['count_miss']} "
            text_score += f"Accuracy: {score['accuracy']:.2f}%\n "
            text_score += f"Rank: {score['rank']} "
            text_score += f"Combo: {score['combo']}x "
            text_score += f"Score: {score['score']:,} "
            text_score += f"PP: {score['pp']}pp\n"
            embed.add_field(name=text_beatmap, value=text_score, inline=False)
        return embed
