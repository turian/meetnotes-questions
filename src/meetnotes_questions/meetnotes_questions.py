import hashlib
import os
import sys
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
        print(f"Modification detected: {file_path}", file=sys.stderr)
        if not os.path.isdir(file_path):
            self.process_file(file_path)

    def on_created(self, event):
        if not event.is_directory:
            print(f"New file created: {event.src_path}", file=sys.stderr)
            self.on_modified(event)

    def on_deleted(self, event):
        print(f"File deleted: {event.src_path}", file=sys.stderr)

    def process_file(self, file_path):
        file_hash = hashlib.md5()

        with open(file_path, "rb") as f:
            buffer = f.read()
        file_hash.update(buffer)

        if self.file_hash.get(file_path, None) != file_hash.digest():
            self.file_hash[file_path] = file_hash.digest()
            print(f"File change detected: {file_path}", file=sys.stderr)

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
    print(f"Starting to watch: {directory_path}", file=sys.stderr)
    observer.schedule(FileWatcher(read_file), directory_path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main():
    openai_token = os.environ.get(
        "OPENAI_TOKEN"
    )  # Recommended to use get in case the variable is not in the environment
    assert openai_token, "OPENAI_TOKEN not found in the environment variables."
    notes_directory = "~/notes"
    absolute_dir_path = os.path.expanduser(notes_directory)
    begin_watching(absolute_dir_path)


if __name__ == "__main__":
    main()
