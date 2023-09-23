from back.taskmanager import TaskManager
from back.tasks.clan_tasks import StoreClanLeaderboardsTask
from back.tasks.user_tasks import (
    StoreUserLeaderboardsTask,
    StorePlayerStats,
    TrackUserPlaytime,
)


def test_backend():
    import api.farmerv2
