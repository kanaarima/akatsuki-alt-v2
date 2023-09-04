from api.utils import get_mods_simple, datetime_to_str, convert_mods
from api.objects import Player, Score, Beatmap
from api.beatmaps import load_beatmap
from datetime import datetime
from typing import List, Dict
import discord


class ScoresView(discord.ui.View):
    def __init__(self, title: str, scores: List[Score], size=7):
        self.title = title
        self.scores = scores
        self.index = 0
        self.desc = True
        self.sort_type = 0
        self.last = True
        self.size = size
        self.sort()
        super().__init__(timeout=180)

    sort_types = ["pp", "date", "score", "accuracy", "mods"]

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = max(0, self.index - 1)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = min(int(len(self.scores) / self.size), self.index + 1)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Last", style=discord.ButtonStyle.gray)
    async def last(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.last:
            self.index = int(len(self.scores) / self.size)
            self.last = False
            button.label = "First"
        else:
            self.index = 0
            self.last = True
            button.label = "Last"
        button._row = 0

        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label=f"Sort: {sort_types[0]}", style=discord.ButtonStyle.gray)
    async def sort_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.index = 0
        self.sort_type += 1
        if self.sort_type > len(self.sort_types) - 1:
            self.sort_type = 0
        self.sort()
        button.label = f"Sort: {self.sort_types[self.sort_type]}"
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label=f"↓", style=discord.ButtonStyle.gray)
    async def sort_dir_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.desc = not self.desc
        button.label = "↓" if self.desc else "↑"
        button.row = 0
        self.sort()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    def sort(self):
        if self.sort_type == 0:
            self.scores.sort(key=lambda x: x["pp"], reverse=self.desc)
        elif self.sort_type == 1:
            self.scores.sort(key=lambda x: x["date"], reverse=self.desc)
        elif self.sort_type == 2:
            self.scores.sort(key=lambda x: x["score"], reverse=self.desc)
        elif self.sort_type == 3:
            self.scores.sort(key=lambda x: x["accuracy"], reverse=self.desc)
        elif self.sort_type == 4:
            self.scores.sort(key=lambda x: x["mods"], reverse=self.desc)

    async def reply(self, message: discord.Message):
        self.message = await message.reply(embed=self.get_embed(), view=self)

    def get_embed(self):
        embed = discord.Embed(
            title=self.title + f" ({self.index}/{int(len(self.scores) / self.size)})"
        )
        i = self.index * self.size
        for score in self.scores[i : i + self.size]:
            beatmap_info = load_beatmap(score["beatmap_id"])
            if not beatmap_info:
                text += "Unknown Beatmap?\n"
                continue
            text_beatmap = f"{beatmap_info['artist']} - {beatmap_info['title']} [{beatmap_info['difficulty_name']}]"
            text_score = f"+{''.join(get_mods_simple(score['mods']))} "
            text_score += f"{score['rank']} "
            text_score += f"{score['combo']}x "
            text_score += f"{score['accuracy']:.2f}% "
            text_score += f"[{score['count_300']}/{score['count_100']}/{score['count_50']}/{score['count_miss']}]\n"
            text_score += f"Score: {score['score']:,} "
            text_score += f"PP: {score['pp']}pp "
            text_score += (
                f"Date: {datetime_to_str(datetime.fromtimestamp(score['date']))}"
            )
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


class StringListView(discord.ui.View):
    def __init__(self, title: str, lists: Dict[str, List[str]], size=7):
        self.title = title
        self.lists = lists
        self.index = 0
        self.list_index = 0
        self.last = True
        self.size = size
        super().__init__(timeout=180)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = max(0, self.index - 1)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = min(
            int(len(self.lists[list(self.lists.keys())[self.list_index]]) / self.size),
            self.index + 1,
        )
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Last", style=discord.ButtonStyle.gray)
    async def last(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.last:
            self.index = int(
                len(self.lists[list(self.lists.keys())[self.list_index]]) / self.size
            )
            self.last = False
            button.label = "First"
        else:
            self.index = 0
            self.last = True
            button.label = "Last"
        button._row = 0

        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Change", style=discord.ButtonStyle.gray)
    async def list_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.index = 0
        self.list_index += 1
        if self.list_index > len(self.lists) - 1:
            self.list_index = 0
        button.label = f"Current: {list(self.lists.keys())[self.list_index]}"
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def reply(self, message: discord.Message):
        self.message = await message.reply(embed=self.get_embed(), view=self)

    def get_embed(self):
        current_list = self.lists[list(self.lists.keys())[self.list_index]]
        embed = discord.Embed(
            title=self.title + f" ({self.index}/{int(len(current_list) / self.size)})"
        )
        i = self.index * self.size
        str = ""
        for string in current_list[i : i + self.size]:
            str += f"{string[:int(1025/self.size)]}\n"
        embed.add_field(name=list(self.lists.keys())[self.list_index], value=str)
        return embed


def get_score_embed(
    player: Player,
    beatmap: Beatmap,
    score: Score,
    title_overwrite=None,
    use_thumbnail=True,
):
    embed = discord.Embed(title=title_overwrite)
    url = f"https://assets.ppy.sh/beatmaps/{beatmap['beatmap_set_id']}/covers/cover@2x.jpg"
    if use_thumbnail:
        embed.set_thumbnail(url=url)
    else:
        embed.set_image(url=url)
    artist = beatmap["artist"]
    title = beatmap["title"]
    difficulty = beatmap["difficulty_name"]
    mods = "".join(get_mods_simple(score["mods"]))
    sr = (
        ""
        if "difficulty" not in beatmap
        else f"[{beatmap['difficulty'][str(convert_mods(score['mods']))]['star_rating']:.1f}*] "
    )
    embed.set_author(
        name=f"{sr}{artist} - {title[:180]} [{difficulty}] +{mods}\n",
        icon_url=f"https://a.akatsuki.gg/{player['id']}",
    )
    combo = (
        "x"
        if "attributes" not in beatmap
        else f"/{beatmap['attributes']['max_combo']}x"
    )
    rank = score["rank"]
    if score["completed"] < 2:
        run = ""
        if "attributes" in beatmap:
            total = (
                score["count_300"]
                + score["count_100"]
                + score["count_50"]
                + score["count_miss"]
            )
            total_map = (
                beatmap["attributes"]["circles"]
                + beatmap["attributes"]["sliders"]
                + beatmap["attributes"]["spinners"]
            )
            run = f" ({int((total/total_map)*100)}%)"
        rank = f"F{run}"
    text = f"➤**{rank} {score['combo']}{combo} {score['accuracy']:.2f}% [{score['count_300']}/{score['count_100']}/{score['count_50']}/{score['count_miss']}] {score['pp']}pp {score['score']:,}**"
    embed.description = text
    return embed
