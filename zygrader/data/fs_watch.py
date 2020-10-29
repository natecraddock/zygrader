"""FS Watch: For monitoring file system folders"""
import os
import threading
import time
import typing


class WatchData:
    def __init__(self, paths: list, identifier: str,
                 callback: typing.Callable[[str], None], *args):
        self.paths = {}
        for path in paths:
            self.paths[path] = 0
        self.init_paths()

        self.identifier = identifier
        self.callback = callback
        self.args = args

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
            self.callback(*self.args)


WATCH_INTEREST = []
WATCH_DELAY = 1


def fs_watch():
    """Watch loop"""
    while True:
        time.sleep(WATCH_DELAY)
        for watch in WATCH_INTEREST:
            watch.check_paths()


def start_fs_watch():
    """Start a file watch thread"""
    watch_thread = threading.Thread(target=fs_watch,
                                    name="FS Watch Thread",
                                    daemon=True)
    watch_thread.start()


def fs_watch_register(paths: list, identifier: str, callback: callable, *args):
    """Register paths with a callback function"""
    WATCH_INTEREST.append(WatchData(paths, identifier, callback, *args))


def fs_watch_unregister(identifier: str):
    """Unregister a path from the file system watch"""
    for watch in WATCH_INTEREST:
        if watch.identifier == identifier:
            WATCH_INTEREST.remove(watch)
            break
