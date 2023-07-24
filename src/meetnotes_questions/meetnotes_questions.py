import asyncio
import hashlib
import json
import os
import queue
import sys
import threading
import time

import openai
import tiktoken
from dotenv import load_dotenv
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

load_dotenv()  # take environment variables from .env.

enc = tiktoken.get_encoding("cl100k_base")


# Assume get_question is an asynchronous function that gets the question.
def get_question(processed_content):
    # Code to get the question goes here...
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=processed_content,
    )
    return response.choices[0].message["content"]


class FileWatcher(FileSystemEventHandler):
    def __init__(self, event_queue):
        super().__init__()
        self.queue = event_queue

    def on_modified(self, event):
        print("File modified event triggered.")
        self.queue.put(("modified", event))
        print("File modified event processed.")

    def on_created(self, event):
        print("File created event triggered.")
        self.queue.put(("created", event))
        print("File created event processed.")

    def on_deleted(self, event):
        print("File deleted event triggered.")
        self.queue.put(("deleted", event))
        print("File deleted event processed.")


def process_file(file_path):
    print(f"File: {file_path}", file=sys.stderr)
    file_content = open(file_path, "rt").read()
    messages = parse_conversation(file_content)
    print("Messages:", messages)
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


def process_event(event_type, event):
    print(f"Event type: {event_type}")
    if event_type in ("modified", "created"):
        if not event.is_directory:
            messages = process_file(event.src_path)
            print("Messages:", json.dumps(messages, indent=2))
            question = get_question(messages)
            print("\nQuestion:", question, "\n")
    elif event_type == "deleted":
        print(f"File deleted: {event.src_path}", file=sys.stderr)


async def begin_watching(path):
    print(path)

    event_queue = queue.Queue()
    file_watcher = FileWatcher(event_queue)

    observer = Observer()
    observer.schedule(file_watcher, path, recursive=True)
    observer.start()

    while True:
        print("Waiting for event...")
        event_type, event = event_queue.get()
        print("Got event: ", event_type, event)
        process_event(event_type, event)
        event_queue.task_done()
    observer.join()


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


async def real_main():
    openai_token = os.environ.get("OPENAI_TOKEN")
    assert openai_token, "OPENAI_TOKEN not found in the environment variables."
    openai.api_key = openai_token
    notes_directory = "~/notes"
    absolute_dir_path = os.path.expanduser(notes_directory)
    assert os.path.isdir(absolute_dir_path), f"Directory not found: {absolute_dir_path}"
    await begin_watching(absolute_dir_path)


def main():
    asyncio.run(real_main())


if __name__ == "__main__":
    main()
