title = "!show (gamemode) (compareto=YYYY-MM-DD) | show your statistics"

documentation = (
    title
    + """\n
Show your game statistics.
Optional: gamemode, compareto
compareto=YYYY-MM-DD: compare current statistics to an older date.
Requires user to be linked on Akatsuki! Alt during that date.
Example: !show compareto=2023-07-27
Available gamemodes:
    std, std_rx, std_ap, taiko, taiko_rx, ctb, ctb_rx, mania
"""
)
