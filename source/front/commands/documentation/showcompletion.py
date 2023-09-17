title = "!showcompletion (completed) (generate) (type=all/ranked_bancho/loved_bancho/ranked_akatsuki/loved_akatsuki) (view=info/maps/maps_missing) (mappers=mapper1,mapper2...) (artists=artist1,artist2...) (tags=tags1,tags2...) | show your completion"

documentation = (
    title
    + """\n
Show your completion statistics.
If you linked account recently, this command might not be available.
Only supports Standard RX.

Optional: completed, generate, type, mappers, artists, tags
    type: filter by ranked status
        available categories: ranked_bancho/loved_bancho/qualified_bancho/ranked_akatsuki/loved_akatsuki/unranked
        example: !showcompletion type=ranked_bancho | shows all bancho ranked clears
    completed: only show completed statistics
    generate: (LEGACY) generate a osdb+csv file. You can use Collection Manager to import these.
        INFO: will get replaced by searchmaps in the future.
    mappers/artists/tags: filter maps by selected filter
        example: mappers=gwb,sotarks   | will get beatmaps by gwb and sotarks
        example: tags=vocaloid,miku    | will get beatmaps with tags vocaloid and miku
        example: artists="hatsune miku"| will get beatmaps with artist "hatsune miku"

"""
)
