from api.objects import Ranking, Player, GamemodeStatistics, gamemodes
from typing import Dict, Tuple, List, Optional
from front.commands.user_commands import _format_gain_string
from config import config
import front.bot as bot
import discord


# Player, Statistics, Ranking score, Ranking pp
def generate_user_leaderboards(
    player_new: Dict[str, Tuple[Player, GamemodeStatistics, Ranking, Ranking]],
    player_old: Dict[str, Tuple[Player, GamemodeStatistics, Ranking, Ranking]],
) -> Dict[str, List[str]]:
    to_post = {}
    for name, gamemode in gamemodes.items():
        player_pp = {}
        player_score = {}
        for player, stats, ranking_score, ranking_pp in player_new[name]:
            if ranking_pp["global_ranking"] > 0:
                player_pp[player["id"]] = [(player, stats, ranking_pp), None]
            if ranking_score["global_ranking"] > 0:
                player_score[player["id"]] = [(player, stats, ranking_score), None]
        for player, stats, ranking_score, ranking_pp in player_old[name]:
            if player["id"] in player_pp:
                player_pp[player["id"]][1] = (player, stats, ranking_pp)
            if player["id"] in player_score:
                player_score[player["id"]][1] = (player, stats, ranking_score)
        to_post[f"player_{name}_pp"] = generate_list(
            list(player_pp.values()), format_player_pp
        )
        to_post[f"player_{name}_score"] = generate_list(
            list(player_score.values()), format_player_score
        )
    totalscore = get_total_score_lb(player_new, player_old)
    for key in totalscore.keys():
        to_post[key] = totalscore[key]
    return to_post


def generate_list(
    data: List[
        Tuple[
            Tuple[Player, GamemodeStatistics, Ranking],
            Optional[Tuple[Player, GamemodeStatistics, Ranking]],
        ]
    ],
    format_func,
) -> List[str]:
    return [
        format_func(new, old)
        for new, old in sorted(data, key=lambda x: x[0][2]["global_ranking"])
    ]


def format_player_pp(
    data_new: Tuple[Player, GamemodeStatistics, Ranking],
    data_old: Tuple[Player, GamemodeStatistics, Ranking],
):
    pp_gain = ""
    rank_gain = ""
    if data_old:
        rank = _format_gain_string(
            gain=data_new[2]["global_ranking"] - data_old[2]["global_ranking"],
        )
        pp = ""
        if "total_pp" in data_old[1]:  # should be always populated, unless old data
            pp = _format_gain_string(
                gain=data_new[1]["total_pp"] - data_old[1]["total_pp"],
                fix="pp",
            )
        rank_gain = f" {rank}"
        pp_gain = f" {pp}"
    return f"#{data_new[2]['global_ranking']} {data_new[0]['name']}{rank_gain} Performance points: {data_new[1]['total_pp']}pp{pp_gain}"


def format_player_score(
    data_new: Tuple[Player, GamemodeStatistics, Ranking],
    data_old: Tuple[Player, GamemodeStatistics, Ranking],
):
    score_gain = ""
    rank_gain = ""
    if data_old:
        rank = _format_gain_string(
            gain=data_new[2]["global_ranking"] - data_old[2]["global_ranking"],
        )
        score = _format_gain_string(
            gain=data_new[1]["ranked_score"] - data_old[1]["ranked_score"]
        )
        rank_gain = f" {rank}"
        score_gain = f" {score}"
    return f"#{data_new[2]['global_ranking']} {data_new[0]['name']}{rank_gain} Ranked score: {data_new[1]['ranked_score']:,}{score_gain}"


def format_player_total_score(
    data_new: Tuple[Player, GamemodeStatistics, Ranking],
    data_old: Tuple[Player, GamemodeStatistics, Ranking],
):
    score_gain = ""
    rank_gain = ""
    if data_old:
        rank = _format_gain_string(
            gain=data_new[2]["global_ranking"] - data_old[2]["global_ranking"],
        )
        score = _format_gain_string(
            gain=data_new[1]["total_score"] - data_old[1]["total_score"]
        )
        rank_gain = f" {rank}"
        score_gain = f" {score}"
    return f"#{data_new[2]['global_ranking']} {data_new[0]['name']}{rank_gain} Total score: {data_new[1]['total_score']:,}{score_gain}"


def get_total_score_lb(player_new, player_old):
    players = {}
    players_old = {}
    res = {}
    for name, gamemode in gamemodes.items():
        players_old[name] = {}
        for player, stats, ranking_score, ranking_pp in player_old[name]:
            if player["id"] not in players_old[name]:
                players_old[name][player["id"]] = (player, stats)
    for name, gamemode in gamemodes.items():
        players[name] = {}
        for player, stats, ranking_score, ranking_pp in player_new[name]:
            if player["id"] not in players[name]:
                players[name][player["id"]] = (player, stats)
    oldplayers = {}
    for name, gamemode in gamemodes.items():
        resl = []
        oldplayers[name] = resl
        players_total_score = sorted(
            list(players_old[name].values()),
            key=lambda x: x[1]["total_score"],
            reverse=True,
        )
        resl.extend(
            (player, stats, Ranking(global_ranking=rank))
            for rank, (player, stats) in enumerate(players_total_score, start=1)
        )
    for name, gamemode in gamemodes.items():
        resl = []
        res[f"player_{name}_total_score"] = resl
        players_total_score = sorted(
            list(players[name].values()),
            key=lambda x: x[1]["total_score"],
            reverse=True,
        )
        for rank, (player, stats) in enumerate(players_total_score, start=1):
            old = None
            for oplayer, ostats, oranking in oldplayers[name]:
                if player["id"] == oplayer["id"]:
                    old = (oplayer, ostats, oranking)
            resl.append(
                format_player_total_score(
                    (player, stats, Ranking(global_ranking=rank)), old
                )
            )
    return res
