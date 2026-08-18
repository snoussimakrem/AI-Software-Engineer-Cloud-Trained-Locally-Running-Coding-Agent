import asyncio
import json
import os
import time
from datetime import datetime, timezone

import httpx

API_KEY = open(os.path.expanduser("~/.config/openrouter/api_key")).read().strip()
API_URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS = {
    "dots-studio/dots-3-note-preview:free": {"max_tokens": 600, "temperature": 0.3},
    "nvidia/nemotron-3.5-lightning:free": {"max_tokens": 1400, "temperature": 0.3},
}

CODING_SYSTEM = (
    "You are an expert Python software engineer. Respond with a complete, "
    "correct solution. Include the code and a brief explanation."
)

BUGFIX_SYSTEM = (
    "You are an expert code reviewer. You will be shown a buggy Python snippet "
    "and a description of the symptom. Identify the exact bug, explain why it "
    "causes the symptom, and provide the fixed code. Base your explanation only "
    "on the actual code shown — do not invent behavior that isn't in the code."
)

TRAJECTORY_SYSTEM = (
    "You are reviewing a coding agent's tool-use trajectory (a sequence of tool "
    "calls and tool results, ending in the agent's final summary). Judge whether "
    "the agent's final summary is strictly and correctly grounded in the actual "
    "tool results shown. If the summary contradicts, ignores, or hallucinates "
    "beyond the tool results, say so explicitly and explain exactly which part "
    "is wrong. If it is correctly grounded, say so and explain why."
)

TASKS = [
    # --- Category A: coding tasks + solutions ---
    {"id": "code-01", "category": "coding_task", "system": CODING_SYSTEM,
     "prompt": "Write a Python function that checks if a string is a palindrome, ignoring case and spaces."},
    {"id": "code-02", "category": "coding_task", "system": CODING_SYSTEM,
     "prompt": "Implement a Python Stack class with push, pop, peek, and is_empty methods."},
    {"id": "code-03", "category": "coding_task", "system": CODING_SYSTEM,
     "prompt": "Write a Python function that merges two already-sorted lists into one sorted list, without using the built-in sort()."},
    {"id": "code-04", "category": "coding_task", "system": CODING_SYSTEM,
     "prompt": "Implement a Python function to find the longest common prefix among a list of strings."},
    {"id": "code-05", "category": "coding_task", "system": CODING_SYSTEM,
     "prompt": "Write a Python function that flattens a nested list of arbitrary depth into a single flat list."},
    {"id": "code-06", "category": "coding_task", "system": CODING_SYSTEM,
     "prompt": "Implement a simple LRU cache in Python with get(key) and put(key, value) methods, fixed capacity."},
    {"id": "code-07", "category": "coding_task", "system": CODING_SYSTEM,
     "prompt": "Write a Python function to detect whether a singly linked list has a cycle, given a Node class with a .next attribute."},

    # --- Category B: bug-fix examples ---
    {"id": "bug-01", "category": "bug_fix", "system": BUGFIX_SYSTEM,
     "prompt": "def divide(a, b):\n    return a / b\n\nSymptom: this function is used in a calculator app and crashes intermittently in production."},
    {"id": "bug-02", "category": "bug_fix", "system": BUGFIX_SYSTEM,
     "prompt": "def get_average(nums):\n    return sum(nums) / len(nums)\n\nSymptom: crashes with a ZeroDivisionError for certain inputs."},
    {"id": "bug-03", "category": "bug_fix", "system": BUGFIX_SYSTEM,
     "prompt": "def binary_search(arr, target):\n    low, high = 0, len(arr)\n    while low < high:\n        mid = (low + high) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            low = mid\n        else:\n            high = mid\n    return -1\n\nSymptom: this function hangs forever on certain inputs instead of returning."},
    {"id": "bug-04", "category": "bug_fix", "system": BUGFIX_SYSTEM,
     "prompt": "def remove_duplicates(lst):\n    for item in lst:\n        if lst.count(item) > 1:\n            lst.remove(item)\n    return lst\n\nSymptom: given [1, 2, 2, 2, 3], this returns [1, 2, 2, 3] instead of [1, 2, 3] — duplicates aren't fully removed."},
    {"id": "bug-05", "category": "bug_fix", "system": BUGFIX_SYSTEM,
     "prompt": "class Counter:\n    def __init__(self):\n        self.count = 0\n    def increment(self):\n        self.count =+ 1\n\nSymptom: calling increment() repeatedly never changes self.count above 1."},
    {"id": "bug-06", "category": "bug_fix", "system": BUGFIX_SYSTEM,
     "prompt": "def factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n - 1)\n\nSymptom: calling factorial(-5) causes a RecursionError instead of a clear error."},
    {"id": "bug-07", "category": "bug_fix", "system": BUGFIX_SYSTEM,
     "prompt": "async def fetch_data(urls):\n    results = []\n    for url in urls:\n        results.append(fetch(url))\n    return results\n\nSymptom: results contains coroutine objects instead of the actual fetched data (fetch is an async function)."},

    # --- Category C: agent trajectory grounding reviews ---
    {"id": "traj-01", "category": "trajectory_review", "system": TRAJECTORY_SYSTEM,
     "prompt": (
         "tool_call: read_file('calculator.py')\n"
         "tool_result: \"def add(a, b):\\n    return a + b\\n\\ndef subtract(a, b):\\n    return a - b\\n\\n"
         "def divide(a, b):\\n    return a / b\\n\"\n"
         "agent_summary: \"I read calculator.py. There is no divide function in this file, only add and subtract.\""
     )},
    {"id": "traj-02", "category": "trajectory_review", "system": TRAJECTORY_SYSTEM,
     "prompt": (
         "tool_call: read_file('calculator.py')\n"
         "tool_result: \"def add(a, b):\\n    return a + b\\n\\ndef divide(a, b):\\n    return a / b\\n\"\n"
         "agent_summary: \"I read calculator.py. It defines add and divide. The divide function does not guard "
         "against b == 0, so it will raise a ZeroDivisionError for that input.\""
     )},
    {"id": "traj-03", "category": "trajectory_review", "system": TRAJECTORY_SYSTEM,
     "prompt": (
         "tool_call: search_code('TODO')\n"
         "tool_result: [\"app.py:12: # TODO: handle timeout\", \"app.py:45: # TODO: add retry logic\"]\n"
         "agent_summary: \"I searched the codebase for TODO comments and found none. The code is complete.\""
     )},
    {"id": "traj-04", "category": "trajectory_review", "system": TRAJECTORY_SYSTEM,
     "prompt": (
         "tool_call: edit_file('utils.py', 'def old_name():', 'def new_name():')\n"
         "tool_result: \"ERROR: old_text not found in utils.py\"\n"
         "agent_summary: \"I renamed the function successfully. The task is done.\""
     )},
    {"id": "traj-05", "category": "trajectory_review", "system": TRAJECTORY_SYSTEM,
     "prompt": (
         "tool_call: list_files()\n"
         "tool_result: [\"main.py\", \"utils.py\", \"tests/test_utils.py\"]\n"
         "tool_call: read_file('utils.py')\n"
         "tool_result: \"def slugify(text):\\n    return text.lower().replace(' ', '-')\\n\"\n"
         "agent_summary: \"utils.py defines a single function, slugify(text), which lowercases the input and "
         "replaces spaces with hyphens. It doesn't strip punctuation, so 'Hello, World!' would become 'hello,-world!'.\""
     )},
]


async def call_model(client: httpx.AsyncClient, model: str, cfg: dict, task: dict) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": task["system"]},
            {"role": "user", "content": task["prompt"]},
        ],
        "max_tokens": cfg["max_tokens"],
        "temperature": cfg["temperature"],
    }
    resp = await client.post(
        API_URL,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    record = {
        "task_id": task["id"],
        "category": task["category"],
        "model": model,
        "prompt": task["prompt"],
        "status_code": resp.status_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if resp.status_code == 200:
        data = resp.json()
        record["response"] = data["choices"][0]["message"]["content"]
        record["usage"] = data.get("usage")
    else:
        record["error"] = resp.text[:1000]
    return record


async def main():
    out_path = "datasets/raw/coding-v1-raw.jsonl"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    results = []
    async with httpx.AsyncClient() as client:
        for task in TASKS:
            for model, cfg in MODELS.items():
                print(f"-> {task['id']} / {model}")
                record = await call_model(client, model, cfg, task)
                results.append(record)
                status = "OK" if record["status_code"] == 200 else f"FAILED ({record['status_code']})"
                print(f"   {status}")
                time.sleep(3)  # stay well under 20 req/min

    with open(out_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    ok = sum(1 for r in results if r["status_code"] == 200)
    print(f"\n{ok}/{len(results)} succeeded. Written to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
