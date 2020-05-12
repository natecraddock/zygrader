"""FS Watch: For monitoring file system folders"""
import os
import threading
import time
import typing

class WatchData:
    def __init__(self, paths: list, identifier: str, callback: typing.Callable[[str], None]):
        self.paths = {}
        for path in paths:
            self.paths[path] = 0
        self.init_paths()

        self.identifier = identifier
        self.callback = callback

    def init_paths(self):
        for path in self.paths.keys():
            self.paths[path] = hash(tuple(os.listdir(path)))

    def check_paths(self):
        changed = False
        for path, hash_id in self.paths.items():
            new_hash = hash(tuple(os.listdir(path)))
            if hash_id != new_hash:
                self.paths[path] = new_hash
                changed = True

        if changed:
            self.callback(self.identifier)

watch_interest = []

def fs_watch():
    """Watch loop"""
    while True:
        time.sleep(5)
        for watch in watch_interest:
            watch.check_paths()

def start_fs_watch():
    """Start a file watch thread"""
    watch_thread = threading.Thread(target=fs_watch, name="FS Watch Thread", daemon=True)
    watch_thread.start()

def fs_watch_register(paths: list, identifier: str, callback: callable):
    """Register paths with a callback function"""
    watch_interest.append(WatchData(paths, identifier, callback))
