from typing import TypedDict

class Player(TypedDict):
    name: str
    clan_id: int
    id: int

class Score(TypedDict):
    beatmap_id: int
    mods: int
    pp: float
    combo: int
    count_300: int
    count_100: int
    count_50: int
    count_miss: int
    accuracy: float
    score: int

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

class GamemodeStatistics:
    total_pp: float
    profile_accuracy: float
    
    count_1s: int