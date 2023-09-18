title = "!searchmaps [unplayed=True] [Filters] | Search beatmaps"

documentation = (
    title
    + """\n
Optional: unplayed=True | returns only unplayed maps
Available Filters:
    comparison: bancho_status=<1 akatsuki_status=>0 mapper=gwb | 
        check if map is unranked on bancho, has leaderboard on akatsuki, and mapper is gwb
    time: approved_date=<2023-07-27 | check if approved date is under specified date
    range comparison: akatsuki_status=1:4 | check if map is ranked and loved
Filterable Options:
    beatmap_id, beatmap_set_id, md5, artist, title, difficulty_name, mapper, 
    bancho_status, akatsuki_status, last_checked, ar, od, cs, length, bpm, 
    max_combo, circles, sliders, spinners, mode, tags, stars_nm, stars_ez, 
    stars_hr, stars_dt, stars_dtez, stars_dthr, approved_date, tags_packs
Extra info:
ranking status: unranked: -2:0 | ranked: 1 | approved: 2 | qualified: 3 | loved: 4
"""
)
