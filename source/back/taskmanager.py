from api.tasks import Task, TaskStatus
from threading import Thread
from typing import List, Dict
import signal
import time


class SignalHandler:
    exit = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.handle)
        signal.signal(signal.SIGTERM, self.handle)

    def handle(self, *args):
        self.exit = True


class TaskManager:
    def __init__(self, tasks: List[Task]):
        self.tasks = tasks

    def start_async(self, task: Task) -> Thread:
        thread = Thread(target=task.run)
        thread.start()
        return thread

    def run_sync(self, tasks: List[Task]):
        for task in tasks:
            task.run()

    def loop(self):
        sighandler = SignalHandler()
        threads: Dict[Task, Thread] = dict()
        sync_thread = None
        while True:
            sync_tasks: List[Task] = list()
            for task in self.tasks:
                if not task.can_run():
                    continue
                if task in threads and threads[task].is_alive():
                    continue
                if task.asynchronous:
                    threads[task] = self.start_async(task)
                else:
                    sync_tasks.append(task)
            if not sync_thread or not sync_thread.is_alive():
                sync_thread = Thread(target=self.run_sync, args=[sync_tasks])
                sync_thread.start()
            if sighandler.exit:
                for task in sync_tasks + list(threads.keys()):
                    task.suspend()
                for thread in threads.values():
                    thread.join()
                sync_thread.join()
                break
            time.sleep(1)
