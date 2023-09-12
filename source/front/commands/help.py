link = "!link (username/userID) | link your akatsuki account"
setdefault = "!setdefault (gamemode) | set your default gamemode"
recent = "!recent (gamemode) | shows your recent play"
show = "!show (gamemode) (compareto=YYYY-MM-DD) | show your statistics"
reset = "!reset | Resets your daily statistics (won't affect stored statistics)"
show1s = "!show1s (gamemode) (new) | show your first places"
showclears = "!showclears (gamemode) (view=ranked_bancho/loved_bancho/qualified_bancho/ranked_akatsuki/loved_akatsuki/unranked) | show your clears"
showcompletion = "!showcompletion (completed) (generate) (type=all/ranked_bancho/loved_bancho/ranked_akatsuki/loved_akatsuki) (view=info/maps/maps_missing) (mappers=mapper1,mapper2...) (artists=artist1,artist2...) (tags=tags1,tags2...) | show your completion"
show1slb = "!show1slb | shows current top 10 by #1 count"
getfile = "!getfile (beatmaps/beatmapsets) (type=akatsuki/akatsuki_ranked/akatsuki_loved) | get files"
help = "\n".join(
    [
        link,
        setdefault,
        recent,
        show,
        reset,
        show1s,
        showclears,
        showcompletion,
        show1slb,
        getfile,
    ]
)
