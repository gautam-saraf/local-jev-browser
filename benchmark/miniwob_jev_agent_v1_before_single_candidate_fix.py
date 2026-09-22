import argparse
import json
import re
import time
from pathlib import Path

import gymnasium as gym
import httpx
import browsergym.miniwob

from browsergym.utils.obs import (
    flatten_axtree_to_str,
)


OPENJEV_URL = "http://127.0.0.1:8000/score"

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

ROOT = Path(__file__).resolve().parent.parent

RESULTS_DIR = (
    ROOT
    / "benchmark"
    / "results"
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def node_field(
    node,
    field,
):
    value = node.get(
        field,
        {},
    )

    if isinstance(
        value,
        dict,
    ):
        return str(
            value.get(
                "value",
                "",
            )
        )

    return str(
        value or ""
    )


def visible_axtree(
    obs,
):
    return flatten_axtree_to_str(
        obs[
            "axtree_object"
        ],
        extra_properties=obs[
            "extra_element_properties"
        ],
        with_visible=True,
        with_clickable=True,
        filter_visible_only=True,
        skip_generic=True,
    )


def extract_goal_text_candidates(
    goal,
):
    """
    Extract possible literal text that the user
    requested to type.

    This is bounded candidate generation:
    Gemma/OpenJEV is still choosing the action.
    """

    values = []

    # Strong patterns first.
    patterns = [
        r'\benter\s+"([^"]+)"',
        r"\benter\s+'([^']+)'",
        r'\btype\s+"([^"]+)"',
        r"\btype\s+'([^']+)'",
        r'\binput\s+"([^"]+)"',
        r"\binput\s+'([^']+)'",
        r'\bwrite\s+"([^"]+)"',
        r"\bwrite\s+'([^']+)'",
    ]

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            goal,
            flags=re.IGNORECASE,
        ):

            candidate = (
                match.group(1)
                .strip()
            )

            if (
                candidate
                and candidate
                not in values
            ):
                values.append(
                    candidate
                )

    # Fallback: quoted strings in goal.
    if not values:

        quoted = re.findall(
            r'"([^"]+)"',
            goal,
        )

        for candidate in quoted:

            candidate = (
                candidate.strip()
            )

            if (
                candidate
                and candidate
                not in values
            ):
                values.append(
                    candidate
                )

    return values


def build_candidates(
    obs,
    goal,
):
    tree = obs[
        "axtree_object"
    ]

    extra = obs[
        "extra_element_properties"
    ]

    text_candidates = (
        extract_goal_text_candidates(
            goal
        )
    )

    candidates = []
    seen = set()

    click_roles = {
        "button",
        "link",
        "checkbox",
        "radio",
        "option",
        "menuitem",
        "tab",
    }

    textbox_roles = {
        "textbox",
        "searchbox",
    }

    for node in tree.get(
        "nodes",
        [],
    ):

        bid = node.get(
            "browsergym_id"
        )

        if not bid:
            continue

        role = (
            node_field(
                node,
                "role",
            )
            .strip()
            .lower()
        )

        name = (
            node_field(
                node,
                "name",
            )
            .strip()
        )

        current_value = (
            node_field(
                node,
                "value",
            )
            .strip()
        )

        properties = extra.get(
            bid,
            {},
        )

        visibility = (
            properties.get(
                "visibility",
                0,
            )
        )

        clickable = bool(
            properties.get(
                "clickable",
                False,
            )
        )

        if visibility < 0.5:
            continue

        # ---------------------------------
        # TEXT INPUT ACTIONS
        # ---------------------------------

        if role in textbox_roles:

            element_name = (
                name
                if name
                else "unnamed textbox"
            )

            for text in text_candidates:

                # Do not keep proposing exactly
                # the value already in the field.
                if current_value == text:
                    continue

                key = (
                    "fill",
                    bid,
                    text,
                )

                if key in seen:
                    continue

                seen.add(
                    key
                )

                candidates.append({
                    "type":
                        "fill",
                    "bid":
                        bid,
                    "text":
                        text,
                    "role":
                        role,
                    "name":
                        element_name,
                    "description":
                        f'FILL {role} '
                        f'"{element_name}" '
                        f'with "{text}"',
                    "browsergym_action":
                        f'fill({json.dumps(bid)}, '
                        f'{json.dumps(text)})',
                })

        # ---------------------------------
        # CLICK ACTIONS
        # ---------------------------------

        if (
            role in click_roles
            or clickable
        ):

            # Clicking an unnamed textbox is
            # usually noise for our bounded set.
            if (
                role in textbox_roles
                and not name
            ):
                continue

            element_name = (
                name
                if name
                else f"unnamed {role or 'element'}"
            )

            key = (
                "click",
                bid,
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            candidates.append({
                "type":
                    "click",
                "bid":
                    bid,
                "role":
                    role,
                "name":
                    element_name,
                "description":
                    f'CLICK '
                    f'{role or "element"} '
                    f'"{element_name}"',
                "browsergym_action":
                    f'click({json.dumps(bid)})',
            })

    return candidates[
        :len(LETTERS)
    ]


def ask_openjev(
    goal,
    page_text,
    candidates,
):
    menu = "\n".join(
        f"{LETTERS[i]}. "
        f"{candidate['description']}"
        for i, candidate
        in enumerate(
            candidates
        )
    )

    context = f"""You are controlling a web browser inside the MiniWoB benchmark.

User goal:
{goal}

Current accessible browser state:
{page_text}

Available browser actions:
{menu}

Choose exactly ONE next action that most directly advances or completes the user's explicit goal.

Important decision rules:
- Choose only from the available actions.
- Match requested text and UI elements precisely.
- If the goal asks to enter or type specific text and the appropriate textbox is empty, fill it first.
- If the requested text is already entered and a submit/confirm control is available, choose the appropriate submit/confirm control.
- If a visible button or link directly matches the requested target, prefer it.
- Do not interact with unrelated controls.
- Do not repeat an action that has already achieved its intended state.
- Return the best action label."""

    options = [
        LETTERS[i]
        for i in range(
            len(candidates)
        )
    ]

    payload = {
        "context":
            context,
        "options":
            options,
        "norm":
            "pmi",
        "chat":
            True,
        "sep":
            "",
    }

    started = (
        time.perf_counter()
    )

    response = httpx.post(
        OPENJEV_URL,
        json=payload,
        timeout=60.0,
    )

    response.raise_for_status()

    latency = (
        time.perf_counter()
        - started
    )

    result = (
        response.json()
    )

    return (
        result,
        latency,
        context,
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--task",
        default=(
            "browsergym/miniwob.enter-text"
        ),
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=6,
    )

    parser.add_argument(
        "--headless",
        action="store_true",
    )

    args = parser.parse_args()

    print()
    print("=" * 70)
    print(
        "GENERIC OPENJEV + BROWSERGYM + MINIWOB"
    )
    print("=" * 70)

    print(
        "Task:",
        args.task,
    )

    print(
        "Seed:",
        args.seed,
    )

    env = gym.make(
        args.task,
        headless=args.headless,
    )

    episode = {
        "task":
            args.task,
        "seed":
            args.seed,
        "architecture":
            "openjev_chat_pmi",
        "steps":
            [],
    }

    success = False

    final_reward = 0.0
    final_raw_reward = None
    final_terminated = False
    final_truncated = False

    try:

        obs, info = env.reset(
            seed=args.seed
        )

        goal = str(
            obs["goal"]
        )

        episode["goal"] = goal

        print()
        print("GOAL:")
        print(goal)

        for step in range(
            1,
            args.max_steps + 1,
        ):

            print()
            print("=" * 70)
            print(
                f"STEP {step}"
            )
            print("=" * 70)

            page_text = (
                visible_axtree(
                    obs
                )
            )

            print()
            print(
                "ACCESSIBILITY TREE:"
            )
            print(
                page_text
            )

            candidates = (
                build_candidates(
                    obs,
                    goal,
                )
            )

            print()
            print(
                "CANDIDATE ACTIONS:"
            )

            for i, candidate in enumerate(
                candidates
            ):

                print(
                    f"{LETTERS[i]} = "
                    f"{candidate['description']} "
                    f"[{candidate['browsergym_action']}]"
                )

            if not candidates:

                print()
                print(
                    "NO CANDIDATES AVAILABLE"
                )

                break

            (
                result,
                decision_latency,
                context,
            ) = ask_openjev(
                goal,
                page_text,
                candidates,
            )

            ranked = sorted(
                result["options"],
                key=lambda x:
                    x["probability"],
                reverse=True,
            )

            print()
            print(
                "OPENJEV RANKING:"
            )

            for item in ranked:

                print(
                    f"{item['option']:>2}  "
                    f"{item['probability'] * 100:9.5f}%"
                )

            best_index = int(
                result[
                    "best_index"
                ]
            )

            best_letter = (
                LETTERS[
                    best_index
                ]
            )

            chosen = (
                candidates[
                    best_index
                ]
            )

            action = (
                chosen[
                    "browsergym_action"
                ]
            )

            print()
            print(
                "MODEL CHOICE:",
                best_letter,
                "=",
                chosen[
                    "description"
                ],
            )

            print(
                "BrowserGym action:",
                action,
            )

            print(
                "Decision latency:",
                f"{decision_latency * 1000:.1f} ms",
            )

            (
                next_obs,
                reward,
                terminated,
                truncated,
                step_info,
            ) = env.step(
                action
            )

            task_info = (
                step_info.get(
                    "task_info",
                    {},
                )
            )

            raw_reward = (
                task_info.get(
                    "RAW_REWARD_GLOBAL"
                )
            )

            reward_reason = (
                task_info.get(
                    "REWARD_REASON"
                )
            )

            done_global = (
                task_info.get(
                    "DONE_GLOBAL"
                )
            )

            last_error = (
                next_obs.get(
                    "last_action_error",
                    "",
                )
            )

            print()
            print(
                "ENV RESULT:"
            )

            print(
                "reward:",
                reward,
            )

            print(
                "RAW_REWARD_GLOBAL:",
                raw_reward,
            )

            print(
                "DONE_GLOBAL:",
                done_global,
            )

            print(
                "terminated:",
                terminated,
            )

            print(
                "truncated:",
                truncated,
            )

            print(
                "last_action_error:",
                last_error,
            )

            step_record = {
                "step":
                    step,
                "axtree":
                    page_text,
                "candidates":
                    candidates,
                "decision_context":
                    context,
                "openjev_response":
                    result,
                "decision_latency_s":
                    decision_latency,
                "chosen_letter":
                    best_letter,
                "chosen_candidate":
                    chosen,
                "reward":
                    float(reward),
                "raw_reward":
                    raw_reward,
                "reward_reason":
                    reward_reason,
                "done_global":
                    done_global,
                "terminated":
                    bool(terminated),
                "truncated":
                    bool(truncated),
                "last_action_error":
                    str(last_error),
            }

            episode[
                "steps"
            ].append(
                step_record
            )

            obs = next_obs

            final_reward = float(
                reward
            )

            final_raw_reward = (
                raw_reward
            )

            final_terminated = bool(
                terminated
            )

            final_truncated = bool(
                truncated
            )

            if (
                terminated
                or truncated
            ):

                success = (
                    float(reward) > 0
                    and
                    bool(terminated)
                    and
                    not bool(
                        last_error
                    )
                )

                break

        episode.update({
            "success":
                success,
            "steps_used":
                len(
                    episode[
                        "steps"
                    ]
                ),
            "final_reward":
                final_reward,
            "final_raw_reward":
                final_raw_reward,
            "final_terminated":
                final_terminated,
            "final_truncated":
                final_truncated,
        })

        print()
        print("=" * 70)
        print(
            "FINAL RESULT"
        )
        print("=" * 70)

        print(
            "Steps used:",
            len(
                episode[
                    "steps"
                ]
            ),
        )

        print(
            "Final reward:",
            final_reward,
        )

        print(
            "Final raw reward:",
            final_raw_reward,
        )

        if success:
            print(
                "MINIWOB_GENERIC_OPENJEV=PASS"
            )
        else:
            print(
                "MINIWOB_GENERIC_OPENJEV=FAIL"
            )

        if not args.headless:

            print()
            print(
                "Browser visible "
                "for 5 seconds..."
            )

            time.sleep(
                5
            )

    finally:

        env.close()

        safe_task = (
            args.task
            .replace(
                "browsergym/miniwob.",
                "",
            )
            .replace(
                "/",
                "_",
            )
        )

        output = (
            RESULTS_DIR
            / (
                "miniwob_openjev_"
                f"{safe_task}_"
                f"seed{args.seed}_"
                f"{int(time.time())}.json"
            )
        )

        output.write_text(
            json.dumps(
                episode,
                indent=2,
                default=str,
            )
        )

        print()
        print(
            "Log saved:"
        )
        print(
            output
        )


if __name__ == "__main__":
    main()
