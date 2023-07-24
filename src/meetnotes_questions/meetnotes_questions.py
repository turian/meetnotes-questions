import asyncio
import hashlib
import json
import os
import sys
import time

import openai
import tiktoken
from dotenv import load_dotenv
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

load_dotenv()  # take environment variables from .env.

enc = tiktoken.get_encoding("cl100k_base")


# Assume get_question is an asynchronous function that gets the question.
async def get_question(processed_content):
    # Code to get the question goes here...
    print(f"Question: Really?")


class FileWatcher(FileSystemEventHandler):
    def __init__(self):
        self.file_hash = {}

    async def process_file(self, file_path):
        file_hash = hashlib.md5()
        file_content = self.read_file(file_path)
        file_hash.update(file_content)

        if self.file_hash.get(file_path, None) != file_hash.digest():
            self.file_hash[file_path] = file_hash.digest()
            print(f"File change detected: {file_path}", file=sys.stderr)

        processed_content = self.process_text(file_content)
        print(
            f"Processed content: {json.dumps(processed_content, indent=2)}",
            file=sys.stderr,
        )

        # fire off an *async* call to get_question
        asyncio.create_task(get_question(processed_content))

    def read_file(self, file_path):
        with open(file_path, "rb") as f:
            buffer = f.read()
        return buffer

    async def on_modified(self, event):
        try:
            file_path = event.src_path
            print(f"Modification detected: {file_path}", file=sys.stderr)
            if not os.path.isdir(file_path):
                await self.process_file(file_path)
        except Exception as e:  # catch the error
            print(f"Exception occurred in method on_modified: {repr(e)}")

    async def on_created(self, event):
        try:
            if not event.is_directory:
                print(f"New file created: {event.src_path}", file=sys.stderr)
                await self.on_modified(event)
        except Exception as e:  # catch the error
            print(f"Exception occurred in method on_created: {repr(e)}")

    def on_deleted(self, event):
        try:
            print(f"File deleted: {event.src_path}", file=sys.stderr)
        except Exception as e:  # catch the error
            print(f"Exception occurred in method on_deleted: {repr(e)}")

    def process_text(self, file_content):
        text = file_content.decode(
            "utf-8"
        )  # decoding required to convert binary data to text
        messages = parse_conversation(text)
        system_message = {
            "role": "system",
            "content": 'You are a junior staff member at a company, and trying to learn more about the business and domain. You are transcribing notes between yourself, your colleagues, and clients/prospects. "Me" means messages by me. Propose intelligent questions to ask in the meeting.',
        }
        kept_messages = []
        for message in reversed(messages):
            total_text = json.dumps([system_message] + [message] + kept_messages)
            if len(enc.encode(total_text)) > 4000:
                break
            kept_messages = [message] + kept_messages
        return [system_message] + kept_messages


def parse_conversation(text):
    segments = text.split("[")[1:]  # Exclude the first split as it will be empty
    conversation = []
    for segment in segments:
        speaker, paragraphs = segment.split("]: ", 1)
        if len(speaker) > 24:
            continue  # Skip the speaker names that are longer than 24 characters
        # conversation.append({"name": speaker, "text": paragraphs})
        conversation.append(
            {
                "role": "user",
                "content": f"{speaker}: {' '.join(paragraphs.splitlines())}",
            }
        )
    return conversation


# Below is the function:
def begin_watching(directory_path):
    loop = asyncio.get_event_loop()
    observer = Observer()
    print(f"Starting to watch: {directory_path}", file=sys.stderr)
    file_watcher = FileWatcher()
    observer.schedule(file_watcher, directory_path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main():
    openai_token = os.environ.get("OPENAI_TOKEN")
    assert openai_token, "OPENAI_TOKEN not found in the environment variables."
    openai.api_key = openai_token
    notes_directory = "~/notes"
    absolute_dir_path = os.path.expanduser(notes_directory)
    assert os.path.isdir(absolute_dir_path), f"Directory not found: {absolute_dir_path}"
    begin_watching(absolute_dir_path)


if __name__ == "__main__":
    main()
