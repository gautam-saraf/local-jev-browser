import json
import re
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright


GOAL = "Search for Alan Turing and open the Alan Turing article."

START_URL = "https://en.wikipedia.org/wiki/Main_Page"

OPENJEV_URL = "http://127.0.0.1:8000/score"

MAX_STEPS = 8
MAX_ACTIONS = 20

LOG_DIR = (
    Path(__file__).resolve().parent.parent
    / "logs"
)
LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

LETTERS = "ABCDEFGHIJKLMNOPQRST"


def label(index):
    return LETTERS[index]


def clean(text):
    return " ".join(
        (text or "").split()
    )


def extract_search_candidate(goal):
    match = re.search(
        r"search\s+for\s+(.+?)(?:\s+and\b|[,.]|$)",
        goal,
        flags=re.IGNORECASE,
    )

    if match:
        return clean(
            match.group(1)
        )

    return "Alan Turing"


SEARCH_TEXT = extract_search_candidate(
    GOAL
)


def visible_text(page):
    try:
        text = page.locator(
            "body"
        ).inner_text(
            timeout=5000
        )
    except Exception:
        return ""

    return clean(text)[:2500]


def goal_keywords():
    words = re.findall(
        r"[A-Za-z0-9]+",
        GOAL.lower(),
    )

    stop = {
        "search",
        "for",
        "and",
        "open",
        "the",
        "article",
    }

    return {
        word
        for word in words
        if word not in stop
        and len(word) > 2
    }


KEYWORDS = goal_keywords()


def relevance(text):
    value = clean(text).lower()

    score = 0

    for keyword in KEYWORDS:
        if keyword in value:
            score += 1

    return score


def find_text_inputs(page):
    candidates = []

    selectors = [
        'input[type="search"]',
        'input[name="search"]',
        'input[type="text"]',
    ]

    seen = set()

    for selector in selectors:

        locator = page.locator(
            selector
        )

        for i in range(
            locator.count()
        ):

            item = locator.nth(i)

            try:
                if not item.is_visible():
                    continue
            except Exception:
                continue

            key = (
                item.get_attribute("id"),
                item.get_attribute("name"),
            )

            if key in seen:
                continue

            seen.add(key)
            candidates.append(item)

    return candidates


def input_name(locator, index):
    for attr in [
        "aria-label",
        "placeholder",
        "name",
        "id",
    ]:
        try:
            value = locator.get_attribute(
                attr
            )

            if value:
                return clean(value)
        except Exception:
            pass

    return f"textbox {index + 1}"


def observe(page):
    actions = []

    # ==================================
    # TEXT INPUTS - highest priority
    # ==================================

    text_inputs = find_text_inputs(page)

    for i, textbox in enumerate(
        text_inputs
    ):

        name = input_name(
            textbox,
            i,
        )

        try:
            value = clean(
                textbox.input_value()
            )
        except Exception:
            value = ""

        if not value:

            actions.append({
                "type": "fill",
                "input_index": i,
                "text": SEARCH_TEXT,
                "description":
                    f'TYPE "{SEARCH_TEXT}" '
                    f'into textbox "{name}"',
            })

        else:

            actions.append({
                "type": "press_enter",
                "input_index": i,
                "value": value,
                "description":
                    f'PRESS ENTER in textbox '
                    f'"{name}" containing '
                    f'"{value}"',
            })

    # ==================================
    # BUTTONS
    # ==================================

    buttons = page.get_by_role(
        "button"
    )

    for i in range(
        buttons.count()
    ):

        button = buttons.nth(i)

        try:
            if not button.is_visible():
                continue

            text = clean(
                button.inner_text()
            )

            if not text:
                text = clean(
                    button.get_attribute(
                        "aria-label"
                    )
                )

        except Exception:
            continue

        if not text:
            continue

        actions.append({
            "type": "button",
            "element_index": i,
            "text": text,
            "description":
                f'CLICK button "{text}"',
        })

    # ==================================
    # LINKS
    #
    # Real pages can contain hundreds.
    # Rank goal-related links first.
    # ==================================

    links = page.get_by_role(
        "link"
    )

    link_actions = []

    for i in range(
        links.count()
    ):

        link = links.nth(i)

        try:
            if not link.is_visible():
                continue

            text = clean(
                link.inner_text()
            )

        except Exception:
            continue

        if not text:
            continue

        link_actions.append({
            "type": "link",
            "element_index": i,
            "text": text,
            "relevance": relevance(text),
            "description":
                f'CLICK link "{text}"',
        })

    link_actions.sort(
        key=lambda x: x["relevance"],
        reverse=True,
    )

    for action in link_actions:
        if len(actions) >= (
            MAX_ACTIONS - 3
        ):
            break

        actions.append(
            action
        )

    # ==================================
    # NAVIGATION
    # ==================================

    actions.append({
        "type": "back",
        "description": "GO BACK",
    })

    actions.append({
        "type": "scroll_down",
        "description": "SCROLL DOWN",
    })

    actions.append({
        "type": "scroll_up",
        "description": "SCROLL UP",
    })

    actions = actions[
        :MAX_ACTIONS
    ]

    return {
        "title": page.title(),
        "url": page.url,
        "visible_text":
            visible_text(page),
        "actions": actions,
        "text_inputs":
            len(text_inputs),
    }


def score_actions(state):
    menu = "\n".join(
        f"{label(i)}. "
        f"{action['description']}"
        for i, action
        in enumerate(
            state["actions"]
        )
    )

    context = f"""You are controlling a real web browser.

User goal:
{GOAL}

Current page title:
{state["title"]}

Current URL:
{state["url"]}

Current visible page text:
{state["visible_text"]}

Available actions:
{menu}

Choose exactly ONE next action that most directly satisfies the user's explicit goal.

Important decision rules:
- Optimize for the user's requested destination.
- Choose only from the available actions.
- Do not invent actions.
- If an empty search textbox is available and the goal requires searching, type the relevant query.
- If the query is already inside the search textbox, submit it.
- If a link directly matches the requested destination, prefer that link.
- Do not choose unrelated navigation.
- Do not go back unless the current page is wrong.
- Do not scroll when the needed action is already visible.

Respond with only the corresponding letter.

Answer:"""

    options = [
        label(i)
        for i in range(
            len(state["actions"])
        )
    ]

    payload = {
        "context": context,
        "options": options,
        "norm": "pmi",
        "chat": True,
        "sep": "",
    }

    started = time.perf_counter()

    with httpx.Client(
        timeout=60
    ) as client:

        response = client.post(
            OPENJEV_URL,
            json=payload,
        )

        response.raise_for_status()

    elapsed = (
        time.perf_counter()
        - started
    )

    return (
        context,
        response.json(),
        elapsed,
    )


def execute(page, state, action):
    kind = action["type"]

    if kind in {
        "fill",
        "press_enter",
    }:

        inputs = find_text_inputs(
            page
        )

        target = inputs[
            action["input_index"]
        ]

        if kind == "fill":

            target.fill(
                action["text"]
            )

        else:

            target.press(
                "Enter"
            )

            try:
                page.wait_for_load_state(
                    "domcontentloaded",
                    timeout=10000,
                )
            except Exception:
                pass

    elif kind == "button":

        target = (
            page.get_by_role(
                "button"
            ).nth(
                action[
                    "element_index"
                ]
            )
        )

        target.click()

    elif kind == "link":

        target = (
            page.get_by_role(
                "link"
            ).nth(
                action[
                    "element_index"
                ]
            )
        )

        target.click()

        try:
            page.wait_for_load_state(
                "domcontentloaded",
                timeout=10000,
            )
        except Exception:
            pass

    elif kind == "back":

        page.go_back()

    elif kind == "scroll_down":

        page.mouse.wheel(
            0,
            800,
        )

    elif kind == "scroll_up":

        page.mouse.wheel(
            0,
            -800,
        )

    else:

        raise RuntimeError(
            f"Unknown action: {kind}"
        )

    page.wait_for_timeout(
        500
    )


def target_reached(page):
    title = page.title().lower()
    url = page.url.lower()

    return (
        "alan turing" in title
        and
        "/wiki/alan_turing"
        in url
    )


def main():
    print()
    print("=" * 60)
    print("REAL-WORLD LOCAL JEV BROWSER AGENT")
    print("=" * 60)

    print("Goal:")
    print(GOAL)

    print()
    print(
        "Extracted search query:",
        SEARCH_TEXT,
    )

    history = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            channel="chrome",
            headless=False,
        )

        page = browser.new_page(
            viewport={
                "width": 1400,
                "height": 900,
            }
        )

        print()
        print(
            "Opening real website:"
        )
        print(START_URL)

        page.goto(
            START_URL,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        success = False

        for step in range(
            1,
            MAX_STEPS + 1,
        ):

            if target_reached(page):
                success = True
                break

            print()
            print("=" * 60)
            print(
                f"STEP {step}"
            )
            print("=" * 60)

            state = observe(page)

            print(
                "Title:",
                state["title"],
            )

            print(
                "URL:",
                state["url"],
            )

            print()
            print(
                "Available actions:"
            )

            for i, action in enumerate(
                state["actions"]
            ):

                print(
                    f"{label(i)} = "
                    f"{action['description']}"
                )

            (
                context,
                decision,
                latency,
            ) = score_actions(
                state
            )

            ranked = sorted(
                decision["options"],
                key=lambda item:
                    item["probability"],
                reverse=True,
            )

            print()
            print(
                "Model ranking:"
            )

            for item in ranked:
                print(
                    f"{item['option'].strip():>2} "
                    f"{item['probability'] * 100:9.5f}%"
                )

            chosen_index = (
                decision[
                    "best_index"
                ]
            )

            chosen = state[
                "actions"
            ][chosen_index]

            print()
            print(
                "MODEL CHOICE:",
                label(
                    chosen_index
                ),
                "=",
                chosen[
                    "description"
                ],
            )

            print(
                "Decision latency:",
                f"{latency * 1000:.1f} ms",
            )

            history.append({
                "step": step,
                "state": state,
                "decision_context":
                    context,
                "decision":
                    decision,
                "chosen_action":
                    chosen,
                "latency_s":
                    latency,
            })

            execute(
                page,
                state,
                chosen,
            )

            if target_reached(
                page
            ):
                success = True
                break

        print()
        print("=" * 60)
        print("FINAL RESULT")
        print("=" * 60)

        print(
            "Final title:",
            page.title(),
        )

        print(
            "Final URL:",
            page.url,
        )

        print(
            "Steps used:",
            len(history),
        )

        if success:
            print()
            print(
                "REAL_WIKIPEDIA_AGENT=PASS"
            )
        else:
            print()
            print(
                "REAL_WIKIPEDIA_AGENT=FAIL"
            )

        log_path = (
            LOG_DIR
            / (
                "real_wikipedia_"
                f"{int(time.time())}.json"
            )
        )

        log_path.write_text(
            json.dumps(
                {
                    "goal": GOAL,
                    "success":
                        success,
                    "final_title":
                        page.title(),
                    "final_url":
                        page.url,
                    "steps":
                        history,
                },
                indent=2,
            )
        )

        print()
        print(
            "Log saved:"
        )
        print(
            log_path
        )

        print()
        print(
            "Browser visible "
            "for 10 seconds..."
        )

        page.wait_for_timeout(
            10000
        )

        browser.close()


if __name__ == "__main__":
    main()
