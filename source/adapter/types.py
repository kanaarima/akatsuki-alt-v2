from typing import TypedDict

old_gamemodes_to_new = {
    "std_vn": "std",
    "std_rx": "std_rx",
    "std_ap": "std_ap",
    "taiko_vn": "taiko",
    "taiko_rx": "taiko_rx",
    "ctb_rx": "ctb_rx",
    "mania_vn": "mania",
    "ctb_vn": "ctb",
}

new_gamemodes_to_old = {v: k for k, v in old_gamemodes_to_new.items()}


class old_stats(TypedDict, total=True):
    performance_points: float
    accuracy: float
    ranked_score: int
    total_score: int
    play_count: int
    first_places: int
    pp_rank: int
    score_rank: int
    fs_rank: int


class old_clan(TypedDict):
    name: str
    tag: str
    id: int
    statistics: dict
