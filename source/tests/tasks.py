from back.taskmanager import TaskManager
from api.tasks import Task, TaskStatus
from time import sleep


class TestTaskSyncA(Task):
    def run(self) -> TaskStatus:
        print("Task sync A started")
        sleep(2)
        print("Task sync A stopped")

    def can_run(self) -> bool:
        return True


class TestTaskSyncB(Task):
    def run(self) -> TaskStatus:
        print("Task sync B started")
        sleep(2)
        print("Task sync B stopped")

    def can_run(self) -> bool:
        return True


class TestTaskASyncA(Task):
    def __init__(self) -> None:
        super().__init__(asynchronous=True)

    def run(self) -> TaskStatus:
        print("Task async A started")
        sleep(5)
        print("Task async A stopped")

    def can_run(self) -> bool:
        return True


class TestTaskASyncB(Task):
    def __init__(self) -> None:
        super().__init__(asynchronous=True)

    def run(self) -> TaskStatus:
        print("Task async B started")
        sleep(1.5)
        print("Task async B stopped")

    def can_run(self) -> bool:
        return True


def test_manager():
    manager = TaskManager(
        [TestTaskSyncA(), TestTaskSyncB(), TestTaskASyncA(), TestTaskASyncB()]
    )
    manager.loop()
