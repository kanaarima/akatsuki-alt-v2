from api.tasks import Task, TaskStatus
from threading import Thread
from typing import List, Dict
from api.logging import logger
from api.files import DataFile
from config import config
import signal
import time


class SignalHandler:
    exit = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.handle)
        signal.signal(signal.SIGTERM, self.handle)

    def handle(self, *args):
        self.exit = True


def name(task: Task):
    return task.__class__.__name__


class TaskManager:
    def __init__(self, tasks: List[Task]):
        self.tasks = tasks
        self.tasks_status = DataFile(
            f"{config['common']['log_directory']}/status.json.gz"
        )
        self.tasks_status.data = {}
        self.tasks_status.save_data()

    def start_async(self, task: Task) -> Thread:
        self.tasks_status.data[name(task)] = "running (async)"
        self.tasks_status.save_data()
        logger.info(f"Task {name(task)} is starting (async)")
        thread = Thread(target=task.run)
        thread.start()
        return thread

    def run_sync(self, tasks: List[Task]):
        for task in tasks:
            self.tasks_status.data[name(task)] = "waiting"
        for task in tasks:
            self.tasks_status.data[name(task)] = "running"
            self.tasks_status.save_data()
            logger.info(f"Task {name(task)} is starting (sync)")
            try:
                task.run()
            except:
                logger.error(f"Task {name(task)} errored out.", exc_info=True)
                self.tasks_status.data[name(task)] = "error"
            else:
                self.tasks_status.data[name(task)] = "completed"
            self.tasks_status.save_data()
            logger.info(f"Task {name(task)} is done (sync)")
        self.tasks_status.save_data()

    def loop(self):
        sighandler = SignalHandler()
        threads: Dict[Task, Thread] = dict()
        sync_thread = None
        while True:
            sync_tasks: List[Task] = list()
            for task in self.tasks:
                if (
                    task.asynchronous
                    and name(task) in self.tasks_status.data
                    and task in threads
                ):
                    if not threads[task].is_alive():
                        logger.info(f"Task {name(task)} is done (async)")
                        self.tasks_status.data.pop(name(task), None)
                        self.tasks_status.save_data()
                if not task.can_run():
                    continue
                if task in threads and threads[task].is_alive():
                    continue
                if task.asynchronous:
                    threads[task] = self.start_async(task)
                else:
                    sync_tasks.append(task)
            if not sync_thread or not sync_thread.is_alive() and sync_tasks:
                sync_thread = Thread(target=self.run_sync, args=[sync_tasks])
                sync_thread.start()
            if sighandler.exit:
                for task in sync_tasks + list(threads.keys()):
                    task.suspend()
                for thread in threads.values():
                    thread.join()
                sync_thread.join()
                self.tasks_status.data = {"backend restart": "running"}
                self.tasks_status.save_data()
                break
            time.sleep(1)
