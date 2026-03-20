import os
import json

MEMORY_FILE = "memory/project_memory.json"


def save_memory(data):
    os.makedirs("memory", exist_ok=True)

    memory = []

    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            try:
                memory = json.load(f)
            except json.JSONDecodeError:
                memory = []

    memory.append(data)

    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []

    with open(MEMORY_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []