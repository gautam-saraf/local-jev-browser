import json
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright


GOAL = "Find the API documentation"
OPENJEV_URL = "http://127.0.0.1:8000/score"

APP_DIR = Path(__file__).resolve().parent
PAGE_PATH = APP_DIR / "demo_page.html"
LOG_DIR = APP_DIR.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def option_label(index: int) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if index >= len(letters):
        raise ValueError("Too many actions")
    return letters[index]


def score_actions(goal, actions):
    menu_lines = []

    for i, action in enumerate(actions):
        label = option_label(i)
        menu_lines.append(
            f"{label}. {action['description']}"
        )

    context = f"""You are controlling a web browser.

User goal:
{goal}

Current browser state:
You are on a page titled "Developer Portal".

Available actions:
{chr(10).join(menu_lines)}

Choose the single action that most directly advances the user toward the goal.
Respond with only the corresponding letter.

Answer:"""

    options = [
        f" {option_label(i)}"
        for i in range(len(actions))
    ]

    payload = {
        "context": context,
        "options": options,
        "norm": "sum",
        "chat": False,
        "sep": "",
    }

    print()
    print("==========================================")
    print("OPENJEV DECISION INPUT")
    print("==========================================")
    print(context)

    started = time.perf_counter()

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            OPENJEV_URL,
            json=payload,
        )
        response.raise_for_status()

    elapsed = time.perf_counter() - started
    result = response.json()

    print()
    print("==========================================")
    print("OPENJEV DECISION OUTPUT")
    print("==========================================")

    ranked = sorted(
        result["options"],
        key=lambda x: x["probability"],
        reverse=True,
    )

    for item in ranked:
        probability = item["probability"] * 100
        print(
            f"{item['option'].strip():>2}  "
            f"{probability:9.5f}%"
        )

    print()
    print("Best option:", result["best"].strip())
    print("Best index :", result["best_index"])
    print(f"HTTP round trip: {elapsed * 1000:.1f} ms")

    return {
        "request": payload,
        "response": result,
        "round_trip_s": elapsed,
    }


def main():
    with sync_playwright() as p:

        chrome_path = Path("/Applications/Google Chrome.app")

        if chrome_path.exists():
            print("Browser backend: installed Google Chrome")
            browser = p.chromium.launch(
                channel="chrome",
                headless=False,
            )
        else:
            print("Browser backend: Playwright Chromium")
            browser = p.chromium.launch(
                headless=False,
            )

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 850,
            }
        )

        page.goto(PAGE_PATH.as_uri())

        print()
        print("==========================================")
        print("BROWSER STATE")
        print("==========================================")
        print("Goal :", GOAL)
        print("Title:", page.title())
        print("URL  :", page.url)

        buttons = page.get_by_role("button")

        actions = []

        for i in range(buttons.count()):
            button = buttons.nth(i)
            text = button.inner_text().strip()

            actions.append({
                "type": "click",
                "element_index": i,
                "text": text,
                "description": f'CLICK button "{text}"',
            })

        actions.append({
            "type": "scroll_down",
            "description": "SCROLL DOWN",
        })

        print()
        print("Detected actions:")

        for i, action in enumerate(actions):
            print(
                f"{option_label(i)} = "
                f"{action['description']}"
            )

        decision = score_actions(
            GOAL,
            actions,
        )

        best_index = decision["response"]["best_index"]

        if best_index < 0 or best_index >= len(actions):
            raise RuntimeError(
                f"Invalid action index: {best_index}"
            )

        chosen = actions[best_index]

        print()
        print("==========================================")
        print("EXECUTING MODEL DECISION")
        print("==========================================")
        print(
            f"{option_label(best_index)} = "
            f"{chosen['description']}"
        )

        if chosen["type"] == "click":
            target = buttons.nth(
                chosen["element_index"]
            )
            target.click()

        elif chosen["type"] == "scroll_down":
            page.mouse.wheel(0, 700)

        page.wait_for_timeout(500)

        result_text = page.locator("#result").inner_text()

        print()
        print("==========================================")
        print("RESULT")
        print("==========================================")
        print(result_text)

        success = (
            result_text.strip()
            == "API DOCUMENTATION FOUND"
        )

        if success:
            print()
            print("JEV_BROWSER_DECISION=PASS")
        else:
            print()
            print("JEV_BROWSER_DECISION=FAIL")

        log_record = {
            "goal": GOAL,
            "page_title": page.title(),
            "page_url": page.url,
            "actions": actions,
            "decision": decision,
            "chosen_action": chosen,
            "result_text": result_text,
            "success": success,
        }

        log_path = LOG_DIR / "first_jev_browser_decision.json"

        log_path.write_text(
            json.dumps(
                log_record,
                indent=2,
            )
        )

        print()
        print("Log saved:")
        print(log_path)

        print()
        print("Browser visible for 8 seconds...")
        page.wait_for_timeout(8000)

        browser.close()


if __name__ == "__main__":
    main()
