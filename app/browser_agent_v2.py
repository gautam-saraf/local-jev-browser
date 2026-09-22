import json
import re
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright


GOAL = "Search for Playwright and open its Python installation guide."
OPENJEV_URL = "http://127.0.0.1:8000/score"
MAX_STEPS = 10

APP_DIR = Path(__file__).resolve().parent
START_PAGE = APP_DIR / "search_demo" / "index.html"
LOG_DIR = APP_DIR.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

TARGET_TEXT = "TARGET_REACHED: PLAYWRIGHT_PYTHON_INSTALLATION"
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def label(index):
    if index >= len(LETTERS):
        raise RuntimeError("Too many actions")
    return LETTERS[index]


def clean_text(text):
    return " ".join((text or "").split())


def extract_text_candidates(goal):
    candidates = []

    search_match = re.search(
        r"search\s+for\s+(.+?)(?:\s+and\b|[,.]|$)",
        goal,
        flags=re.IGNORECASE,
    )

    if search_match:
        candidates.append(search_match.group(1).strip())

    # A second candidate to make the decision non-trivial.
    if "Python" in goal:
        candidates.append("Python")

    unique = []

    for item in candidates:
        item = clean_text(item)

        if item and item.lower() not in {
            x.lower() for x in unique
        }:
            unique.append(item)

    return unique


def page_text(page):
    try:
        text = page.locator("body").inner_text()
    except Exception:
        return ""

    return clean_text(text)[:1800]


def element_name(locator, fallback):
    for attribute in ["aria-label", "placeholder", "name"]:
        try:
            value = locator.get_attribute(attribute)

            if value:
                return clean_text(value)
        except Exception:
            pass

    return fallback


def observe(page, text_candidates):
    actions = []

    # Text boxes
    textboxes = page.get_by_role("textbox")

    for i in range(textboxes.count()):
        textbox = textboxes.nth(i)

        try:
            if not textbox.is_visible():
                continue
        except Exception:
            continue

        name = element_name(
            textbox,
            f"textbox {i + 1}",
        )

        try:
            value = clean_text(textbox.input_value())
        except Exception:
            value = ""

        if not value:
            for candidate in text_candidates:
                actions.append({
                    "type": "fill",
                    "element_index": i,
                    "text": candidate,
                    "description":
                        f'TYPE "{candidate}" into textbox "{name}"',
                })
        else:
            actions.append({
                "type": "press_enter",
                "element_index": i,
                "description":
                    f'PRESS ENTER in textbox "{name}" containing "{value}"',
            })

            actions.append({
                "type": "clear",
                "element_index": i,
                "description":
                    f'CLEAR textbox "{name}" containing "{value}"',
            })

    # Buttons
    buttons = page.get_by_role("button")

    for i in range(buttons.count()):
        button = buttons.nth(i)

        try:
            if not button.is_visible():
                continue

            text = clean_text(button.inner_text())
        except Exception:
            continue

        if not text:
            text = element_name(
                button,
                f"button {i + 1}",
            )

        actions.append({
            "type": "button",
            "element_index": i,
            "description":
                f'CLICK button "{text}"',
        })

    # Links
    links = page.get_by_role("link")

    for i in range(links.count()):
        link = links.nth(i)

        try:
            if not link.is_visible():
                continue

            text = clean_text(link.inner_text())
        except Exception:
            continue

        if not text:
            continue

        actions.append({
            "type": "link",
            "element_index": i,
            "description":
                f'CLICK link "{text}"',
        })

    if page.url != START_PAGE.as_uri():
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

    return {
        "title": page.title(),
        "url": page.url,
        "visible_text": page_text(page),
        "actions": actions[:26],
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

Choose exactly ONE next action that most directly satisfies the user's explicit goal.

Important decision rules:
- Optimize for the user's requested destination, not the normal reading order of a website or documentation site.
- If an available action directly names or semantically matches the destination requested by the user, prefer that action.
- Do not open introductory or prerequisite material when the explicitly requested destination is already available.
- If an empty search textbox is available and the goal requires searching, first type the most relevant search term.
- If the correct search text is already present, submit it using the Search button or Enter.
- On a search results page, choose the result most directly related to the user's goal.
- Choose only from the available actions.
- Do not invent an action.
- Do not go back unless the current page is wrong.
- Do not scroll when a relevant destination is already visible.

Respond with only the corresponding letter.

Answer:"""

    options = [
        f"{label(i)}"
        for i in range(len(state["actions"]))
    ]

    payload = {
        "context": context,
        "options": options,
        "norm": "pmi",
        "chat": True,
        "sep": "",
    }

    started = time.perf_counter()

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            OPENJEV_URL,
            json=payload,
        )
        response.raise_for_status()

    elapsed = time.perf_counter() - started

    return context, response.json(), elapsed


def execute(page, action):
    kind = action["type"]

    if kind == "fill":
        target = page.get_by_role("textbox").nth(
            action["element_index"]
        )
        target.fill(action["text"])

    elif kind == "press_enter":
        target = page.get_by_role("textbox").nth(
            action["element_index"]
        )
        target.press("Enter")
        page.wait_for_load_state("domcontentloaded")

    elif kind == "clear":
        target = page.get_by_role("textbox").nth(
            action["element_index"]
        )
        target.fill("")

    elif kind == "button":
        target = page.get_by_role("button").nth(
            action["element_index"]
        )
        target.click()
        page.wait_for_load_state("domcontentloaded")

    elif kind == "link":
        target = page.get_by_role("link").nth(
            action["element_index"]
        )
        target.click()
        page.wait_for_load_state("domcontentloaded")

    elif kind == "back":
        page.go_back()
        page.wait_for_load_state("domcontentloaded")

    elif kind == "scroll_down":
        page.mouse.wheel(0, 700)

    elif kind == "scroll_up":
        page.mouse.wheel(0, -700)

    else:
        raise RuntimeError(f"Unknown action: {kind}")

    page.wait_for_timeout(350)


def target_reached(page):
    return TARGET_TEXT in page_text(page)


def main():
    text_candidates = extract_text_candidates(GOAL)
    run_log = []

    print()
    print("==============================================")
    print("LOCAL JEV BROWSER AGENT V2")
    print("==============================================")
    print("Goal:")
    print(GOAL)

    print()
    print("Text candidates extracted from goal:")
    for candidate in text_candidates:
        print("-", candidate)

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

        success = False

        for step in range(1, MAX_STEPS + 1):

            if target_reached(page):
                success = True
                break

            print()
            print("==============================================")
            print(f"STEP {step}")
            print("==============================================")

            state = observe(
                page,
                text_candidates,
            )

            print("Title:", state["title"])
            print("URL  :", state["url"])

            print()
            print("Visible text:")
            print(state["visible_text"])

            print()
            print("Available actions:")

            for i, action in enumerate(state["actions"]):
                print(
                    f"{label(i)} = "
                    f"{action['description']}"
                )

            context, decision, latency = score_actions(state)

            ranked = sorted(
                decision["options"],
                key=lambda x: x["probability"],
                reverse=True,
            )

            print()
            print("Model ranking:")

            for item in ranked:
                print(
                    f"{item['option'].strip():>2} "
                    f"{item['probability'] * 100:9.5f}%"
                )

            best_index = decision["best_index"]

            if best_index < 0 or best_index >= len(state["actions"]):
                raise RuntimeError(
                    f"Invalid model action index: {best_index}"
                )

            chosen = state["actions"][best_index]

            print()
            print(
                "MODEL CHOICE:",
                label(best_index),
                "=",
                chosen["description"],
            )

            print(
                f"Decision HTTP round trip: "
                f"{latency * 1000:.1f} ms"
            )

            run_log.append({
                "step": step,
                "state": state,
                "decision_context": context,
                "decision": decision,
                "chosen_action": chosen,
                "round_trip_s": latency,
            })

            execute(page, chosen)

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
            print("JEV_BROWSER_AGENT_V2=PASS")
        else:
            print()
            print("JEV_BROWSER_AGENT_V2=FAIL")

        log_path = (
            LOG_DIR
            / f"browser_agent_v2_{int(time.time())}.json"
        )

        log_path.write_text(
            json.dumps(
                {
                    "goal": GOAL,
                    "success": success,
                    "text_candidates": text_candidates,
                    "steps_used": len(run_log),
                    "final_title": page.title(),
                    "final_url": page.url,
                    "steps": run_log,
                },
                indent=2,
            )
        )

        print()
        print("Log saved:")
        print(log_path)

        print()
        print("Browser visible for 10 seconds...")
        page.wait_for_timeout(10000)

        browser.close()


if __name__ == "__main__":
    main()
