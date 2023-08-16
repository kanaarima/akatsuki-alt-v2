from back.taskmanager import TaskManager
from back.tasks.clan_tasks import StoreClanLeaderboardsTask


def test_backend():
    manager = TaskManager([StoreClanLeaderboardsTask()])
    manager.loop()
