import time
from pathlib import Path

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler


MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "third_party"
    / "open-jev"
    / "models"
    / "gemma-3-4b-it"
)

GOAL = (
    "Search for Playwright and open its "
    "Python installation guide."
)

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


def make_context():
    menu = "\n".join(
        f"{LETTERS[i]}. {action}"
        for i, action in enumerate(ACTIONS)
    )

    return f"""You are controlling a web browser.

User goal:
{GOAL}

Current page title:
Playwright Python

Current visible page text:
Playwright Python Documentation for using Playwright with Python. Introduction Installation API Reference Examples Back to results

Available actions:
{menu}

Choose exactly ONE next action that most directly satisfies the user's explicit goal.

Important decision rules:
- Optimize for the user's requested destination, not the normal reading order of a website or documentation site.
- If an available action directly names or semantically matches the destination requested by the user, prefer that action.
- Do not open introductory or prerequisite material when the explicitly requested destination is already available.
- Choose only from the listed actions.
- Do not invent an action.
- Do not scroll when a relevant destination is already visible.

Respond with ONLY the corresponding letter.
Do not output JSON.
Do not explain your answer."""


print("=" * 60)
print("GENERATIVE SINGLE-LETTER DIAGNOSTIC")
print("=" * 60)

print()
print("Loading model:")
print(MODEL_PATH)

start = time.perf_counter()

model, tokenizer = load(
    str(MODEL_PATH)
)

print(
    f"Model load: "
    f"{time.perf_counter() - start:.2f}s"
)

context = make_context()

messages = [
    {
        "role": "user",
        "content": context,
    }
]

prompt = tokenizer.apply_chat_template(
    messages,
    add_generation_prompt=True,
)

print()
print("Goal:")
print(GOAL)

print()
print("Available actions:")

for i, action in enumerate(ACTIONS):
    print(
        f"{LETTERS[i]} = {action}"
    )

print()
print("Generating ONE decision token...")

start = time.perf_counter()

raw = generate(
    model=model,
    tokenizer=tokenizer,
    prompt=prompt,
    max_tokens=1,
    sampler=make_sampler(
        temp=0.0
    ),
    verbose=False,
)

elapsed = (
    time.perf_counter()
    - start
)

choice = raw.strip().upper()

print()
print("=" * 60)
print("RESULT")
print("=" * 60)

print("Raw output :", repr(raw))
print("Choice     :", choice)

if (
    choice
    and
    choice[0] in LETTERS
):
    index = LETTERS.index(
        choice[0]
    )

    print(
        "Action     :",
        ACTIONS[index],
    )

print(
    "Latency    :",
    f"{elapsed * 1000:.1f} ms",
)

print()
print("Correct expected action:")
print('B = CLICK link "Installation"')
