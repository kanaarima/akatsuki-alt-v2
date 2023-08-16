from pathlib import Path
import json
import gzip
import time


class DataFile:
    def __init__(self, filepath) -> None:
        # Create parent directory
        Path([item[::-1] for item in filepath[::-1].split("/", 1)][::-1][0]).mkdir(
            parents=True, exist_ok=True
        )
        self.filepath = filepath
        self.data = None

    def load_data(self, default={}):
        self.wait_lock()
        self.lock()
        try:
            with gzip.open(self.filepath, "r") as fin:
                self.data = json.loads(fin.read().decode("utf-8"))
        except:
            self.data = default
        self.unlock()

    def save_data(self):
        self.wait_lock()
        if not self.data:
            self.load_data()
        self.lock()
        with gzip.open(self.filepath, "w") as fout:
            fout.write(json.dumps(self.data).encode("utf-8"))
        self.unlock()

    def delete(self):
        Path(self.filepath).unlink(missing_ok=True)

    def wait_lock(self):
        while Path(self.filepath + ".lock").exists():
            time.sleep(0.1)

    def lock(self):
        Path(self.filepath + ".lock").touch(exist_ok=True)

    def unlock(self):
        Path(self.filepath + ".lock").unlink(missing_ok=True)


def exists(filepath):
    return Path(filepath).exists()
