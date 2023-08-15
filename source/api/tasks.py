from api.files import DataFile
from enum import Enum
import config


class TaskStatus(Enum):
    SUCCESS = 0
    SUSPENDED = 1
    FAILED = 2


class Task:
    def __init__(self, asynchronous=False) -> None:
        self.asynchronous = asynchronous
        self.task_id = type(self).__name__
        self.file = DataFile(
            f"{config.config['common']['data_directory']}/tasks/{self.task_id}.json.gz"
        )
        self.suspended = False

    def can_run(self) -> bool:
        return False

    def suspend(self):
        self.suspended = True
        self.file.save_data()

    def run(self) -> TaskStatus:
        self.suspended = False

    def _finish(self) -> TaskStatus:
        self.file.delete()
        return TaskStatus.SUCCESS
