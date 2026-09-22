import json
import re
import time
from pathlib import Path

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
from playwright.sync_api import sync_playwright


GOAL = "Search for Playwright and open its Python installation guide."
MAX_STEPS = 10

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent

MODEL_PATH = (
    ROOT_DIR
    / "third_party"
    / "open-jev"
    / "models"
    / "gemma-3-4b-it"
)

START_PAGE = (
    APP_DIR
    / "search_demo"
    / "index.html"
)

TARGET_TEXT = (
    "TARGET_REACHED: "
    "PLAYWRIGHT_PYTHON_INSTALLATION"
)

LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def label(index):
    if index >= len(LETTERS):
        raise RuntimeError(
            "More than 26 actions."
        )

    return LETTERS[index]


def clean(text):
    return " ".join(
        (text or "").split()
    )


def extract_text_candidates(goal):
    candidates = []

    match = re.search(
        r"search\s+for\s+(.+?)"
        r"(?:\s+and\b|[,.]|$)",
        goal,
        flags=re.IGNORECASE,
    )

    if match:
        candidates.append(
            clean(
                match.group(1)
            )
        )

    if "Python" in goal:
        candidates.append(
            "Python"
        )

    unique = []

    for item in candidates:

        if (
            item
            and
            item.lower()
            not in {
                x.lower()
                for x in unique
            }
        ):
            unique.append(
                item
            )

    return unique


TEXT_CANDIDATES = (
    extract_text_candidates(
        GOAL
    )
)


def page_text(page):
    try:
        value = (
            page.locator("body")
            .inner_text()
        )
    except Exception:
        return ""

    return clean(value)[:1800]


def element_name(
    locator,
    fallback,
):
    for attribute in [
        "aria-label",
        "placeholder",
        "name",
    ]:

        try:
            value = (
                locator
                .get_attribute(attribute)
            )

            if value:
                return clean(value)

        except Exception:
            pass

    return fallback


def observe(page):
    actions = []

    # -----------------------------
    # TEXTBOXES
    # -----------------------------

    textboxes = (
        page.get_by_role(
            "textbox"
        )
    )

    for i in range(
        textboxes.count()
    ):

        box = textboxes.nth(i)

        try:
            if not box.is_visible():
                continue
        except Exception:
            continue

        name = element_name(
            box,
            f"textbox {i + 1}",
        )

        try:
            value = clean(
                box.input_value()
            )
        except Exception:
            value = ""

        if not value:

            for candidate in (
                TEXT_CANDIDATES
            ):

                actions.append({
                    "type": "fill",
                    "element_index": i,
                    "text": candidate,
                    "description":
                        f'TYPE "{candidate}" '
                        f'into textbox "{name}"',
                })

        else:

            actions.append({
                "type":
                    "press_enter",
                "element_index": i,
                "description":
                    f'PRESS ENTER in textbox '
                    f'"{name}" containing '
                    f'"{value}"',
            })

            actions.append({
                "type": "clear",
                "element_index": i,
                "description":
                    f'CLEAR textbox "{name}" '
                    f'containing "{value}"',
            })

    # -----------------------------
    # BUTTONS
    # -----------------------------

    buttons = (
        page.get_by_role(
            "button"
        )
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

    # -----------------------------
    # LINKS
    # -----------------------------

    links = (
        page.get_by_role(
            "link"
        )
    )

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

        actions.append({
            "type": "link",
            "element_index": i,
            "description":
                f'CLICK link "{text}"',
        })

    if (
        page.url
        != START_PAGE.as_uri()
    ):
        actions.append({
            "type": "back",
            "description":
                "GO BACK",
        })

    actions.append({
        "type": "scroll_down",
        "description":
            "SCROLL DOWN",
    })

    actions.append({
        "type": "scroll_up",
        "description":
            "SCROLL UP",
    })

    return {
        "title":
            page.title(),
        "url":
            page.url,
        "visible_text":
            page_text(page),
        "actions":
            actions[:26],
    }


def build_prompt(state):
    menu = "\n".join(
        f"{label(i)}. "
        f"{action['description']}"
        for i, action
        in enumerate(
            state["actions"]
        )
    )

    return f"""You are controlling a web browser.

User goal:
{GOAL}

Current page title:
{state["title"]}

Current visible page text:
{state["visible_text"]}

Available actions:
{menu}

Choose exactly ONE next action that most directly satisfies the user's goal.

Rules:
- Choose only from the available actions.
- Do not invent an action.
- If an empty search textbox is available and searching is required, type the relevant search term.
- If the correct query is already present, submit it.
- If a visible link directly matches the requested destination, prefer it.
- Optimize for the explicit user goal rather than normal reading order.

Respond with ONLY the corresponding single letter.

For example:
A

Do not output JSON.
Do not explain your answer.
Do not output any other text."""


def parse_generation(
    raw,
    number_of_actions,
):
    stripped = raw.strip().upper()

    allowed = LETTERS[
        :number_of_actions
    ]

    exact_letter_valid = (
        len(stripped) == 1
        and stripped in allowed
    )

    choice = None

    if exact_letter_valid:
        choice = stripped

    else:
        # Secondary recovery parser.
        # We record this as a format violation.
        match = re.search(
            r"\b([A-Z])\b",
            stripped,
        )

        if match:
            candidate = (
                match.group(1)
                .upper()
            )

            if candidate in allowed:
                choice = candidate

    valid_choice = (
        choice is not None
        and choice in allowed
    )

    format_violation = (
        not exact_letter_valid
    )

    return {
        "raw": raw,
        "exact_letter_valid":
            exact_letter_valid,
        "format_violation":
            format_violation,
        "choice":
            choice,
        "valid_choice":
            valid_choice,
    }


def generate_decision(
    model,
    tokenizer,
    state,
):
    user_prompt = (
        build_prompt(state)
    )

    messages = [{
        "role": "user",
        "content": user_prompt,
    }]

    prompt = (
        tokenizer
        .apply_chat_template(
            messages,
            add_generation_prompt=True,
        )
    )

    started = (
        time.perf_counter()
    )

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

    latency = (
        time.perf_counter()
        - started
    )

    parsed = parse_generation(
        raw,
        len(
            state["actions"]
        ),
    )

    return (
        user_prompt,
        raw,
        parsed,
        latency,
    )


def execute(
    page,
    action,
):
    kind = action["type"]

    if kind == "fill":

        (
            page
            .get_by_role("textbox")
            .nth(
                action[
                    "element_index"
                ]
            )
            .fill(
                action["text"]
            )
        )

    elif kind == "press_enter":

        (
            page
            .get_by_role("textbox")
            .nth(
                action[
                    "element_index"
                ]
            )
            .press("Enter")
        )

        page.wait_for_load_state(
            "domcontentloaded"
        )

    elif kind == "clear":

        (
            page
            .get_by_role("textbox")
            .nth(
                action[
                    "element_index"
                ]
            )
            .fill("")
        )

    elif kind == "button":

        (
            page
            .get_by_role("button")
            .nth(
                action[
                    "element_index"
                ]
            )
            .click()
        )

        page.wait_for_load_state(
            "domcontentloaded"
        )

    elif kind == "link":

        (
            page
            .get_by_role("link")
            .nth(
                action[
                    "element_index"
                ]
            )
            .click()
        )

        page.wait_for_load_state(
            "domcontentloaded"
        )

    elif kind == "back":

        page.go_back()

        page.wait_for_load_state(
            "domcontentloaded"
        )

    elif kind == "scroll_down":

        page.mouse.wheel(
            0,
            700,
        )

    elif kind == "scroll_up":

        page.mouse.wheel(
            0,
            -700,
        )

    else:

        raise RuntimeError(
            f"Unknown action: {kind}"
        )

    page.wait_for_timeout(
        350
    )


def target_reached(page):
    return (
        TARGET_TEXT
        in page_text(page)
    )


def main():
    print()
    print("=" * 60)
    print("GENERATIVE SINGLE-LETTER GEMMA BASELINE")
    print("=" * 60)

    print("Model:")
    print(MODEL_PATH)

    print()
    print("Goal:")
    print(GOAL)

    print()
    print(
        "Loading SAME Gemma 3 4B "
        "used by OpenJEV..."
    )

    load_started = (
        time.perf_counter()
    )

    model, tokenizer = load(
        str(MODEL_PATH)
    )

    load_latency = (
        time.perf_counter()
        - load_started
    )

    print(
        f"Model load: "
        f"{load_latency:.2f}s"
    )

    sampler_type = (
        "greedy / temperature 0"
    )

    print(
        "Generation:",
        sampler_type,
    )

    history = []

    invalid_outputs = 0
    format_violations = 0

    with sync_playwright() as p:

        browser = (
            p.chromium.launch(
                channel="chrome",
                headless=False,
            )
        )

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 850,
            }
        )

        page.goto(
            START_PAGE.as_uri()
        )

        success = False
        agent_error = None

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
                prompt,
                raw,
                parsed,
                latency,
            ) = generate_decision(
                model,
                tokenizer,
                state,
            )

            print()
            print(
                "RAW MODEL OUTPUT:"
            )
            print(
                repr(raw)
            )

            print()
            print(
                "Exact single-letter output:",
                parsed[
                    "exact_letter_valid"
                ],
            )

            print(
                "Format violation:",
                parsed[
                    "format_violation"
                ],
            )

            print(
                "Parsed choice:",
                parsed["choice"],
            )

            print(
                "Valid action:",
                parsed[
                    "valid_choice"
                ],
            )

            print(
                "Generation latency:",
                f"{latency * 1000:.1f} ms",
            )

            if parsed[
                "format_violation"
            ]:
                format_violations += 1

            step_record = {
                "step": step,
                "state": state,
                "prompt": prompt,
                "raw_output": raw,
                "parsed": parsed,
                "generation_latency_s":
                    latency,
            }

            if not parsed[
                "valid_choice"
            ]:

                invalid_outputs += 1

                agent_error = (
                    "INVALID_GENERATED_ACTION"
                )

                step_record[
                    "execution"
                ] = "NOT_EXECUTED"

                history.append(
                    step_record
                )

                print()
                print(
                    "GENERATED ACTION "
                    "IS INVALID."
                )

                print(
                    "Stopping run."
                )

                break

            choice_index = (
                LETTERS.index(
                    parsed["choice"]
                )
            )

            chosen = (
                state["actions"][
                    choice_index
                ]
            )

            print()
            print(
                "MODEL CHOICE:",
                parsed["choice"],
                "=",
                chosen[
                    "description"
                ],
            )

            step_record[
                "chosen_action"
            ] = chosen

            history.append(
                step_record
            )

            execute(
                page,
                chosen,
            )

            if target_reached(page):
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
            "Steps:",
            len(history),
        )

        print(
            "Format violations:",
            format_violations,
        )

        print(
            "Invalid outputs:",
            invalid_outputs,
        )

        if agent_error:
            print(
                "Agent error:",
                agent_error,
            )

        print()

        if success:
            print(
                "GENERATIVE_LETTER_BASELINE=PASS"
            )
        else:
            print(
                "GENERATIVE_LETTER_BASELINE=FAIL"
            )

        result = {
            "architecture":
                "generative_single_letter",
            "model":
                str(MODEL_PATH),
            "goal":
                GOAL,
            "success":
                success,
            "model_load_s":
                load_latency,
            "steps_used":
                len(history),
            "format_violations":
                format_violations,
            "invalid_outputs":
                invalid_outputs,
            "agent_error":
                agent_error,
            "final_title":
                page.title(),
            "final_url":
                page.url,
            "steps":
                history,
        }

        output = (
            LOG_DIR
            / (
                "generative_letter_baseline_"
                f"{int(time.time())}.json"
            )
        )

        output.write_text(
            json.dumps(
                result,
                indent=2,
            )
        )

        print()
        print("Log:")
        print(output)

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
