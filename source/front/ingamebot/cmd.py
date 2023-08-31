from osu.objects.player import Player
from front.commands.user_commands import _parse_args
import api.akatsuki as akatsuki
import api.beatmaps as beatmaps
import api.farmer as farmer


def ping(player: Player, message, args):
    player.send_message("pong!")


def recommend(player: Player, message, args):
    _, stats = akatsuki.get_user_stats(player.id, no_1s=True)
    total_pp = stats["std_rx"][0]["total_pp"]
    target = total_pp / 20
    min_pp = target - 20
    max_pp = target + 20
    mods = None
    mods_include = []
    mods_exclude = ["EZ", "FL"]
    parsed = _parse_args(args, nodefault=True)
    if "min_pp" in parsed:
        if not parsed["min_pp"].isnumeric():
            player.send_message("pp value should be a number.")
            return
        min_pp = int(parsed["min_pp"])
        max_pp = min_pp + 20
    if "max_pp" in parsed:
        if not parsed["max_pp"].isnumeric():
            player.send_message("pp value should be a number.")
            return
        max_pp = int(parsed["max_pp"])
    if "mods" in parsed:
        mods = parsed["mods"].upper()
    if "include_mods" in parsed:
        mods_include = [
            parsed["include_mods"][i : i + 2]
            for i in range(0, len(parsed["include_mods"]), 2)
        ]
    if "exclude_mods" in parsed:
        mods_exclude = [
            parsed["exclude_mods"][i : i + 2]
            for i in range(0, len(parsed["exclude_mods"]), 2)
        ]
    recommend = farmer.recommend(
        pp_min=min_pp,
        pp_max=max_pp,
        mods=mods,
        mods_include=mods_include,
        mods_exclude=mods_exclude,
    )
    beatmap = beatmaps.load_beatmap(recommend[0]["beatmap_id"])
    link = f"osu://b/{beatmap['beatmap_id']}"
    title = f"{beatmap['title']} [{beatmap['difficulty_name']}] +{recommend[0]['mods']} {int(recommend[0]['average_pp'])} (confidence: {recommend[0]['weight']*100:.2f}%)"
    player.send_message(f"[{link} {title}]")


def help(player: Player, message, args):
    player.send_message(
        f"KompirBot made by [https://akatsuki.gg/u/91076?mode=0&rx=1 Adachi].\nCommands:\n!recommend (min_pp=pp) (max_pp=pp) (mods=mods) (include_mods=mods) (exclude_mods=mods) | recommends a farm map"
    )
