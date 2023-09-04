from api.objects import Ranking, Player, Clan, GamemodeStatistics, gamemodes
from typing import Dict, Tuple, List, Optional
from front.commands.user_commands import _format_gain_string
from config import config
import front.bot as bot
import discord


# Clan, Statistics, Ranking 1s, Ranking pp
def generate_clan_leaderboards(
    clan_new: Dict[str, Tuple[Clan, GamemodeStatistics, Ranking, Ranking]],
    clan_old: Dict[str, Tuple[Clan, GamemodeStatistics, Ranking, Ranking]],
) -> Dict[str, List[str]]:
    to_post = {}
    for name, gamemode in gamemodes.items():
        clan_pp = {}
        clan_1s = {}
        for clan, stats, ranking_1s, ranking_pp in clan_new[name]:
            if ranking_pp["global_ranking"] > 0:
                clan_pp[clan["clan_id"]] = [(clan, stats, ranking_pp), None]
            if ranking_1s["global_ranking"] > 0:
                clan_1s[clan["clan_id"]] = [(clan, stats, ranking_1s), None]
        for clan, stats, ranking_1s, ranking_pp in clan_old[name]:
            if clan["clan_id"] in clan_pp:
                clan_pp[clan["clan_id"]][1] = (clan, stats, ranking_pp)
            if clan["clan_id"] in clan_1s:
                clan_1s[clan["clan_id"]][1] = (clan, stats, ranking_1s)
        to_post[f"clan_{name}_pp"] = generate_list(
            list(clan_pp.values()), format_clan_pp
        )
        to_post[f"clan_{name}_1s"] = generate_list(
            list(clan_1s.values()), format_clan_1s
        )
    return to_post


def generate_list(
    data: List[
        Tuple[
            Tuple[Clan, GamemodeStatistics, Ranking],
            Optional[Tuple[Clan, GamemodeStatistics, Ranking]],
        ]
    ],
    format_func,
) -> List[str]:
    return [
        format_func(new, old)
        for new, old in sorted(data, key=lambda x: x[0][2]["global_ranking"])
    ]


def format_clan_pp(
    data_new: Tuple[Clan, GamemodeStatistics, Ranking],
    data_old: Tuple[Clan, GamemodeStatistics, Ranking],
):
    pp_gain = ""
    rank_gain = ""
    if data_old:
        rank = _format_gain_string(
            gain=data_new[2]["global_ranking"] - data_old[2]["global_ranking"],
        )
        pp = ""
        if "total_pp" in data_old[1]:
            pp = _format_gain_string(
                gain=data_new[1]["total_pp"] - data_old[1]["total_pp"],
                fix="pp",
            )
        rank_gain = f" {rank}"
        pp_gain = f" {pp}"
    tag = ""
    if "clan_tag" in data_new[0] and data_new[0]["clan_tag"]:
        tag = f" [{data_new[0]['clan_tag']}]"
    return f"#{data_new[2]['global_ranking']} {data_new[0]['clan_name']}{tag}{rank_gain} Performance points: {data_new[1]['total_pp']}pp{pp_gain}"


def format_clan_1s(
    data_new: Tuple[Clan, GamemodeStatistics, Ranking],
    data_old: Tuple[Clan, GamemodeStatistics, Ranking],
):
    fp_gain = ""
    rank_gain = ""
    if data_old:
        rank = _format_gain_string(
            gain=data_new[2]["global_ranking"] - data_old[2]["global_ranking"],
        )
        fp = ""
        if "total_1s" in data_old[1]:
            fp = _format_gain_string(
                gain=data_new[1]["total_1s"] - data_old[1]["total_1s"]
            )
        rank_gain = f" {rank}"
        fp_gain = f" {fp}"
    tag = f" [{data_new[0]['clan_tag']}]"
    return f"#{data_new[2]['global_ranking']} {data_new[0]['clan_name']}{tag}{rank_gain} First places: {data_new[1]['total_1s']}{fp_gain}"
