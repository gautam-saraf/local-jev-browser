import json
import time
from pathlib import Path

import httpx


URL = "http://127.0.0.1:8000/score"

ACTIONS = [
    'CLICK link "Introduction"',
    'CLICK link "Installation"',
    'CLICK link "API Reference"',
    'CLICK link "Examples"',
    'CLICK link "Back to results"',
    'GO BACK',
    'SCROLL DOWN',
    'SCROLL UP',
]

LETTERS = "ABCDEFGH"

GOAL = (
    "Search for Playwright and open its "
    "Python installation guide."
)

PAGE_TITLE = "Playwright Python"

VISIBLE_TEXT = (
    "Playwright Python Documentation for using "
    "Playwright with Python. Introduction Installation "
    "API Reference Examples Back to results"
)


def menu():
    return "\n".join(
        f"{LETTERS[i]}. {action}"
        for i, action in enumerate(ACTIONS)
    )


BASELINE = f"""You are controlling a web browser.

User goal:
{GOAL}

Current page title:
{PAGE_TITLE}

Current visible page text:
{VISIBLE_TEXT}

Available actions:
{menu()}

Choose exactly ONE next action that most directly advances the user toward the goal.

Rules:
- Choose only from the available actions.
- Do not invent an action.
- Prefer direct progress over unrelated navigation.
- Avoid scrolling unless necessary.

Respond with only the corresponding letter.

Answer:"""


GOAL_FOCUSED = f"""You are controlling a web browser.

User goal:
{GOAL}

Current page title:
{PAGE_TITLE}

Current visible page text:
{VISIBLE_TEXT}

Available actions:
{menu()}

Choose exactly ONE next action that most directly satisfies the user's explicit goal.

Important decision rules:
- Optimize for the user's requested destination, not the normal reading order of a documentation site.
- If an available action directly names or semantically matches the destination requested by the user, prefer that action.
- Do not open introductory or prerequisite material when the explicitly requested destination is already available.
- Choose only from the listed actions.
- Do not invent an action.
- Do not scroll when the relevant destination is already visible.

Respond with only the corresponding letter.

Answer:"""


TESTS = [
    {
        "name": "BASELINE_SUM",
        "context": BASELINE,
        "norm": "sum",
        "chat": False,
        "options": [f" {x}" for x in LETTERS],
    },
    {
        "name": "GOAL_FOCUSED_SUM",
        "context": GOAL_FOCUSED,
        "norm": "sum",
        "chat": False,
        "options": [f" {x}" for x in LETTERS],
    },
    {
        "name": "GOAL_FOCUSED_CHAT_PMI",
        "context": GOAL_FOCUSED,
        "norm": "pmi",
        "chat": True,
        "options": list(LETTERS),
    },
]


all_results = []

for test in TESTS:

    payload = {
        "context": test["context"],
        "options": test["options"],
        "norm": test["norm"],
        "chat": test["chat"],
        "sep": "",
    }

    start = time.perf_counter()

    with httpx.Client(timeout=60) as client:
        response = client.post(
            URL,
            json=payload,
        )
        response.raise_for_status()

    elapsed = time.perf_counter() - start

    result = response.json()

    print()
    print("=" * 60)
    print(test["name"])
    print("=" * 60)

    ranked = sorted(
        result["options"],
        key=lambda x: x["probability"],
        reverse=True,
    )

    for item in ranked:
        letter = item["option"].strip()
        index = LETTERS.index(letter)

        print(
            f"{letter}  "
            f"{item['probability'] * 100:10.6f}%  "
            f"{ACTIONS[index]}"
        )

    best = result["best"].strip()
    best_index = result["best_index"]

    print()
    print("BEST LETTER :", best)
    print("BEST ACTION :", ACTIONS[best_index])
    print(
        "ROUND TRIP :",
        f"{elapsed * 1000:.1f} ms",
    )

    all_results.append({
        "test": test["name"],
        "payload": payload,
        "result": result,
        "best_action": ACTIONS[best_index],
        "round_trip_s": elapsed,
    })


output_dir = (
    Path(__file__).resolve().parent.parent
    / "experiments"
)

output_dir.mkdir(
    parents=True,
    exist_ok=True,
)

output = (
    output_dir
    / "installation_decision_diagnostic.json"
)

output.write_text(
    json.dumps(
        all_results,
        indent=2,
    )
)

print()
print("=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
print("Expected correct action:")
print('B = CLICK link "Installation"')
print()
print("Saved:")
print(output)
