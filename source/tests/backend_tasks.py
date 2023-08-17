from back.taskmanager import TaskManager
from back.tasks.clan_tasks import StoreClanLeaderboardsTask
from back.tasks.user_tasks import StoreUserLeaderboardsTask, StorePlayerStats


def test_backend():
    manager = TaskManager(
        [StoreClanLeaderboardsTask(), StoreUserLeaderboardsTask(), StorePlayerStats()]
    )
    manager.loop()
