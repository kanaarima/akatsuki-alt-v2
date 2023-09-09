from typing import TypedDict, Optional, Dict, List


class Player(TypedDict):
    name: str
    country: str
    clan_id: int
    id: int


class Score(TypedDict):
    id: int
    beatmap_id: int
    score: int
    combo: int
    pp: float
    count_300: int
    count_100: int
    count_50: int
    count_miss: int
    accuracy: float
    mods: int
    mode: int
    rank: str
    date: int
    completed: int


class BeatmapAttributes(TypedDict):
    ar: float
    od: float
    cs: float
    length: int
    bpm: float
    max_combo: int
    circles: int
    sliders: int
    spinners: int
    mode: int


class BeatmapDifficulty(TypedDict):
    speed_note_count: int
    flashlight_rating: float
    speed_rating: float
    star_rating: float
    aim_rating: float
    flashlight_pp: float
    speed_pp: float
    aim_pp: float
    acc_pp: float
    pp_100: float
    pp_99: float
    pp_98: float
    pp_97: float
    pp_95: float
    pp_90: float


class RankedStatus(TypedDict):
    bancho: int
    akatsuki: int


class Beatmap(TypedDict):
    beatmap_id: int
    beatmap_set_id: int
    md5: str
    artist: str
    title: str
    difficulty_name: str
    mapper: str
    tags: List[str]
    status: Optional[RankedStatus]
    attributes: Optional[BeatmapAttributes]
    difficulty: Optional[Dict[int, BeatmapDifficulty]]


class Clan(TypedDict):
    clan_id: int
    clan_name: str
    clan_tag: str


class GamemodeStatistics(TypedDict):
    total_pp: float
    total_1s: int
    profile_accuracy: float
    max_combo: int
    play_count: int
    play_time: int
    level: int
    watched_replays: int
    total_score: int
    ranked_score: int
    total_hits: int


class Ranking(TypedDict):
    global_ranking: int
    country_ranking: int


class Gamemode(TypedDict):
    mode: int
    relax: int


gamemodes = {
    "std": Gamemode(mode=0, relax=0),
    "std_rx": Gamemode(mode=0, relax=1),
    "std_ap": Gamemode(mode=0, relax=2),
    "taiko": Gamemode(mode=1, relax=0),
    "taiko_rx": Gamemode(mode=1, relax=1),
    "ctb": Gamemode(mode=2, relax=0),
    "ctb_rx": Gamemode(mode=2, relax=1),
    "mania": Gamemode(mode=3, relax=0),
}

gamemodes_full = {
    "std": "Standard",
    "std_rx": "Standard Relax",
    "std_ap": "Standard Autopilot",
    "taiko": "Taiko",
    "taiko_rx": "Taiko Relax",
    "ctb": "Catch the beat",
    "ctb_rx": "Catch the beat Relax",
    "mania": "Mania",
}


class LinkedPlayer(TypedDict):
    user_id: int
    full_tracking: bool  # True: linked from discord
    render_permission: bool
