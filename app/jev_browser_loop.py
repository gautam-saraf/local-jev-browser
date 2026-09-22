import json
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright


GOAL = "Find and open the Installation Guide for the API documentation."
OPENJEV_URL = "http://127.0.0.1:8000/score"
MAX_STEPS = 8

APP_DIR = Path(__file__).resolve().parent
START_PAGE = APP_DIR / "multi_step_site" / "index.html"
LOG_DIR = APP_DIR.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

TARGET_TEXT = "TARGET_REACHED: LOCAL_BROWSER_JEV_INSTALLATION_GUIDE"


def label(index):
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    if index >= len(letters):
        raise RuntimeError("Too many candidate actions")

    return letters[index]


def get_visible_text(page):
    try:
        text = page.locator("body").inner_text()
    except Exception:
        return ""

    text = " ".join(text.split())

    return text[:1200]


def observe(page):
    actions = []

    links = page.get_by_role("link")

    for i in range(links.count()):
        link = links.nth(i)

        try:
            text = link.inner_text().strip()
        except Exception:
            continue

        if not text:
            continue

        actions.append({
            "type": "link",
            "index": i,
            "text": text,
            "description": f'CLICK link "{text}"',
        })

    buttons = page.get_by_role("button")

    for i in range(buttons.count()):
        button = buttons.nth(i)

        try:
            text = button.inner_text().strip()
        except Exception:
            continue

        if not text:
            continue

        actions.append({
            "type": "button",
            "index": i,
            "text": text,
            "description": f'CLICK button "{text}"',
        })

    actions.append({
        "type": "back",
        "description": "GO BACK",
    })

    actions.append({
        "type": "scroll_down",
        "description": "SCROLL DOWN",
    })

    return {
        "title": page.title(),
        "url": page.url,
        "visible_text": get_visible_text(page),
        "actions": actions,
    }


def score_actions(state):
    menu = []

    for i, action in enumerate(state["actions"]):
        menu.append(
            f"{label(i)}. {action['description']}"
        )

    context = f"""You are controlling a web browser.

User goal:
{GOAL}

Current page title:
{state["title"]}

Current visible page text:
{state["visible_text"]}

Available actions:
{chr(10).join(menu)}

Choose the single action that most directly advances the user toward the goal.

Use the page state and goal together.
Do not invent an action.
Choose only from the available actions.

Respond with only the corresponding letter.

Answer:"""

    options = [
        f" {label(i)}"
        for i in range(len(state["actions"]))
    ]

    payload = {
        "context": context,
        "options": options,
        "norm": "sum",
        "chat": False,
        "sep": "",
    }

    start = time.perf_counter()

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            OPENJEV_URL,
            json=payload,
        )
        response.raise_for_status()

    round_trip = time.perf_counter() - start

    result = response.json()

    return context, result, round_trip


def execute(page, action):
    if action["type"] == "link":
        page.get_by_role("link").nth(
            action["index"]
        ).click()

        page.wait_for_load_state("domcontentloaded")

    elif action["type"] == "button":
        page.get_by_role("button").nth(
            action["index"]
        ).click()

    elif action["type"] == "back":
        page.go_back()
        page.wait_for_load_state("domcontentloaded")

    elif action["type"] == "scroll_down":
        page.mouse.wheel(0, 700)

    else:
        raise RuntimeError(
            f"Unknown action type: {action['type']}"
        )

    page.wait_for_timeout(300)


def target_reached(page):
    return TARGET_TEXT in get_visible_text(page)


def main():
    run_log = []

    with sync_playwright() as p:

        chrome_path = Path(
            "/Applications/Google Chrome.app"
        )

        if chrome_path.exists():
            browser = p.chromium.launch(
                channel="chrome",
                headless=False,
            )
        else:
            browser = p.chromium.launch(
                headless=False,
            )

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 850,
            }
        )

        page.goto(START_PAGE.as_uri())

        print()
        print("==============================================")
        print("LOCAL JEV MULTI-STEP BROWSER AGENT")
        print("==============================================")
        print("Goal:")
        print(GOAL)

        success = False

        for step in range(1, MAX_STEPS + 1):

            print()
            print("==============================================")
            print(f"STEP {step}")
            print("==============================================")

            if target_reached(page):
                success = True
                break

            state = observe(page)

            print("Title:", state["title"])
            print("URL  :", state["url"])

            print()
            print("Visible text:")
            print(state["visible_text"])

            print()
            print("Available actions:")

            for i, action in enumerate(
                state["actions"]
            ):
                print(
                    f"{label(i)} = "
                    f"{action['description']}"
                )

            context, decision, round_trip = (
                score_actions(state)
            )

            ranked = sorted(
                decision["options"],
                key=lambda item: item["probability"],
                reverse=True,
            )

            print()
            print("Model ranking:")

            for item in ranked:
                print(
                    f"{item['option'].strip():>2} "
                    f"{item['probability'] * 100:9.5f}%"
                )

            chosen_index = decision["best_index"]

            if (
                chosen_index < 0
                or chosen_index >= len(state["actions"])
            ):
                raise RuntimeError(
                    f"Invalid action index: {chosen_index}"
                )

            chosen = state["actions"][chosen_index]

            print()
            print(
                "MODEL CHOICE:",
                label(chosen_index),
                "=",
                chosen["description"],
            )

            print(
                f"Decision HTTP round trip: "
                f"{round_trip * 1000:.1f} ms"
            )

            step_log = {
                "step": step,
                "state": state,
                "decision_context": context,
                "decision": decision,
                "chosen_action": chosen,
                "round_trip_s": round_trip,
            }

            run_log.append(step_log)

            execute(
                page,
                chosen,
            )

            if target_reached(page):
                success = True
                break

        print()
        print("==============================================")
        print("FINAL RESULT")
        print("==============================================")

        print("Final title:", page.title())
        print("Final URL  :", page.url)
        print("Steps used :", len(run_log))

        if success:
            print()
            print(
                "JEV_MULTI_STEP_BROWSER_AGENT=PASS"
            )
        else:
            print()
            print(
                "JEV_MULTI_STEP_BROWSER_AGENT=FAIL"
            )

        output = {
            "goal": GOAL,
            "success": success,
            "steps_used": len(run_log),
            "final_title": page.title(),
            "final_url": page.url,
            "steps": run_log,
        }

        log_path = (
            LOG_DIR
            / "multi_step_browser_run.json"
        )

        log_path.write_text(
            json.dumps(
                output,
                indent=2,
            )
        )

        print()
        print("Log saved:")
        print(log_path)

        print()
        print(
            "Browser visible for 10 seconds..."
        )

        page.wait_for_timeout(10000)

        browser.close()


if __name__ == "__main__":
    main()
