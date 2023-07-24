import asyncio
import hashlib
import json
import os
import sys
import time
from asyncio import Queue

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
    def __init__(self, queue: Queue):
        super().__init__()
        self.queue = queue

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


async def process_file(file_path):
    print(f"File created: {file_path}", file=sys.stderr)
    file_content = open(file_path, "rb").read().decode("utf-8")
    text = file_content.decode(
        "utf-8"
    )  # decoding required to convert binary data to text
    messages = parse_conversation(text)
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


async def process_event(event_type, event):
    print(f"Event type: {event_type}")
    if event_type in ("modified", "created"):
        if not event.is_directory:
            await process_file(event.src_path)
    elif event_type == "deleted":
        print(f"File deleted: {event.src_path}", file=sys.stderr)


async def begin_watching(path):
    print(path)
    queue = Queue()

    event_handler = FileWatcher(queue)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while True:
            print("Waiting for event...")
            event_type, event = await queue.get()
            print("Got event: ", event_type, event)
            await process_event(event_type, event)
            queue.task_done()
    except KeyboardInterrupt:
        observer.stop()
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
