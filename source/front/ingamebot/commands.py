from front.commands.user_commands import _parse_args
from api.utils import get_mods, mods_from_string
from osu.objects.player import Player

from api.objects import gamemodes
import api.akatsuki as akatsuki
import api.beatmaps as beatmaps
from api.files import DataFile
import api.farmer as farmer
import api.farmerv2 as farmerv2

from typing import List, Callable, Optional
from dataclasses import dataclass
from config import config
from osu import Game


@dataclass
class Command:
    triggers: List[str]
    function: Callable
    doc: Optional[str]


commands: List[Command] = []


def command(*aliases: List[str]) -> Callable:
    def wrapper(f: Callable) -> Callable:
        commands.append(Command(triggers=aliases, function=f, doc=f.__doc__))
        return f

    return wrapper


@command("ping")
def ping(player: Player, message, args, game: Game):
    player.send_message("pong!")


@command("recommend", "r", "cook")
def recommend(player: Player, message, args, game: Game):
    """<min_pp=pp> <max_pp=pp> <mods=mods> <include_mods=mods> <exclude_mods=mods> <algo=old/auto/model_name> <magic=true>- Recommends a farm map"""

    skip_id = []
    if game.server == "akatsuki.gg":
        # Fetch user stats
        _, stats = akatsuki.get_user_stats(player.id, no_1s=True)
        top100 = akatsuki.get_user_best(player.id, gamemodes["std_rx"])

        # Exclude top play
        # TODO: Exclude all plays that are already fced?
        skip_id = [play["beatmap_id"] for play in top100[0]]
        total_pp = stats["std_rx"][0]["total_pp"]
    else:
        total_pp = player.pp
    # Calculate min/max pp

    target = total_pp / 20
    min_pp = target - 20
    max_pp = target + 20

    mods_include = []
    mods_exclude = ["EZ", "FL"]
    algo = "old"
    matches_threshold = 0.85
    enable_apvn = False
    # Parse command arguments
    parsed = _parse_args(args, nodefault=True)

    if "magic" in parsed:
        enable_apvn = True
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

    if "threshold" in parsed:
        try:
            matches_threshold = float(parsed["threshold"])
        except:
            player.send_message("threshold value should be a number.")
            return

    if "include_mods" in parsed:
        mods_include = [
            parsed["include_mods"][i : i + 2]
            for i in range(0, len(parsed["include_mods"]), 2)
        ]
        for mod in mods_include:
            if mod in mods_exclude:
                mods_exclude.remove(mod)
    if "exclude_mods" in parsed:
        mods_exclude = [
            parsed["exclude_mods"][i : i + 2]
            for i in range(0, len(parsed["exclude_mods"]), 2)
        ]
    if "algo" in parsed:
        algo = parsed["algo"].lower().split(",")
        if algo == "auto":
            algo = [
                "aim",
                "stream",
            ]  # TODO: automatically chose algorithmn by top 100 plays
    mods = parsed["mods"].upper() if "mods" in parsed else None
    if mods:
        mods_exclude = []
        mods_include = []
    if algo == "old":
        recommend = farmer.recommend(
            pp_min=min_pp,
            pp_max=max_pp,
            mods=mods,
            mods_include=mods_include,
            mods_exclude=mods_exclude,
            skip_id=skip_id,
        )

        if not (beatmap := beatmaps.load_beatmap(recommend[0]["beatmap_id"])):
            player.send_message("Failed to load beatmap.")
            return
        title = f"{beatmap['title']} [{beatmap['difficulty_name']}] +{recommend[0]['mods']} {int(recommend[0]['average_pp'])}pp (confidence: {recommend[0]['weight']*100:.2f}%)"
    else:
        if enable_apvn:
            recommend = farmerv2.recommend_next(
                pp_min=min_pp,
                pp_max=max_pp,
                mods=mods_from_string(mods) if mods else None,
                mods_include=mods_include,
                mods_exclude=mods_exclude,
                servers=['bancho', 'akatsuki'] if game.server == "akatsuki.gg" else ['bancho']
                skip_id=skip_id,
                models=algo,
            )
        else:
            recommend = farmer.recommend_next(
                pp_min=min_pp,
                pp_max=max_pp,
                mods=mods,
                mods_include=mods_include,
                mods_exclude=mods_exclude,
                skip_id=skip_id,
                matches_types=algo,
                matches_threshold=matches_threshold,
            )
        if not recommend:
            player.send_message("Nothing found.")
            return
        recommend = recommend[0]
        threshold = recommend["threshold"]
        algo = recommend["match"]
        mods = "".join(get_mods(recommend["future"]["mods"]))

        if not (beatmap := beatmaps.load_beatmap(recommend["future"]["beatmap_id"])):
            player.send_message("Failed to load beatmap.")
            return
        title = f"{beatmap['title']} [{beatmap['difficulty_name']}] +{mods} {int(recommend['pp_avg'])}pp (algo: {algo}, confidence: {threshold*100:.2f}%)"
    link = f"osu://b/{beatmap['beatmap_id']}"
    player.send_message(f"[{link} {title}]")


@command("recommend_score", "rs", "scoer")
def recommend_score(player: Player, message, args, game: Game):
    """- Recommends a score farm map"""
    skip_id = []
    # TODO: FIX THIS
    # if scores.exists():
    #     scores.load_data()
    #     skip_id.extend(
    #         int(beatmapid) for beatmapid in list(scores.data["std_rx"].keys())
    #     )

    beatmap_metadata = farmer.recommend_score(skip_id, 1)[0]
    beatmap = beatmaps.load_beatmap(beatmap_metadata["beatmap_id"])
    link = f"osu://b/{beatmap['beatmap_id']}"
    title = f"{beatmap['title']} [{beatmap['difficulty_name']}] {int(beatmap_metadata['max_score']):,} (score/minute: {int(beatmap_metadata['score_minute']):,})"
    player.send_message(f"[{link} {title}]")


@command("models", "chefs")
def show_models(player: Player, message, args, game: Game):
    """- Shows recommendation algorithms"""
    models = [
        ("old", "old recommendation algorithm"),
        ("auto", "automatically choose a model for you"),
    ]
    models.extend(farmer.models)
    str = "".join(f"{model[0]} - {model[1]}\n" for model in models)
    player.send_message(str)


@command("help", "h")
def help(player: Player, message, args, game: Game):
    """- Shows this message"""

    # Create command string if they have a __doc__ string
    command_strings = [
        f"{config['discord']['bot_prefix']}{cmd.triggers[0]} {cmd.doc}"
        for cmd in commands
        if cmd.doc
    ]

    player.send_message(
        "\n".join(
            [
                "KompirBot made by [https://akatsuki.gg/u/91076?mode=0&rx=1 Adachi].",
                "",
                "Commands",
                "--------",
                "\n".join(command_strings),
            ]
        )
    )
