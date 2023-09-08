from api.utils import mods_from_string
import api.farmer as farmer
import discord


async def check_beatmap_type(full: str, split: list[str], message: discord.Message):
    if not farmer.futures:
        await message.reply("Farm maps are still being calculated!")
        return
    if len(split) < 2:
        await message.reply("Wrong syntax! Usage: show_beatmap_type beatmap_id mods")
        return
    if not split[0].isnumeric():
        await message.reply("Wrong syntax! Usage: show_beatmap_type beatmap_id mods")
        return
    beatmap_id = int(split[0])
    mods = mods_from_string(split[1])
    print(beatmap_id)
    for future in farmer.futures:
        if future["beatmap_id"] == beatmap_id and future["mods"] == mods:
            embed = discord.Embed(
                title=f"Beatmap type is {future['most_likely']}",
                description="Model matches:",
            )
            for model_name, likely in future["matches"].items():
                embed.add_field(name=model_name, value=f"{likely*100:.2f}%")
            await message.reply(embed=embed)
            return
    await message.reply("Beatmap has no matches.")
