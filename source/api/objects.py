from typing import TypedDict

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

class Beatmap(TypedDict):
    beatmap_id: int
    beatmap_set_id: int
    artist: str
    title: str
    difficulty: str
    bpm: float
    star_rating: float
    aim_rating: float
    speed_rating: float
    length: int
    drain_time: int
    max_combo: int
    mode: int

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
    total_score: int
    ranked_score: int
    total_hits: int

class Ranking(TypedDict):
    global_ranking: int
    country_ranking: int
    