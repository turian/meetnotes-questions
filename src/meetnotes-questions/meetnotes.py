import hashlib
import os
import time

from dotenv import load_dotenv
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

load_dotenv()  # take environment variables from .env.


class FileWatcher(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
        self.file_hash = {}

    def on_modified(self, event):
        file_path = event.src_path
        if not os.path.isdir(file_path) and file_path.endswith(".txt"):
            file_hash = hashlib.md5()
            with open(file_path, "rb") as f:
                buffer = f.read()
                file_hash.update(buffer)

            if self.file_hash.get(file_path, None) != file_hash.digest():
                self.file_hash[file_path] = file_hash.digest()

                if callable(self.callback):
                    self.callback(file_path)


def read_file(file_path):
    with open(file_path, "r") as file:
        text = file.read()
    return process_text(text)


def process_text(text):
    result = text.upper()
    return result


def begin_watching(directory_path):
    observer = Observer()
    observer.schedule(FileWatcher(read_file), directory_path, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    openai_token = os.environ("OPENAI_TOKEN")
    assert openai_token
    notes_directory = "~/notes"
    absolute_dir_path = os.path.abspath(notes_directory)
    begin_watching(absolute_dir_path)
