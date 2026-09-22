import json
import time
from pathlib import Path

import gymnasium as gym
import httpx
import browsergym.miniwob

from browsergym.utils.obs import (
    flatten_axtree_to_str,
)


TASK = "browsergym/miniwob.click-button"
SEED = 42

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


def collect_click_candidates(
    obs,
):
    """
    Generic visible/clickable candidate extraction.

    We are NOT looking for the target text here.
    We expose browser elements and let OpenJEV choose.
    """

    tree = obs[
        "axtree_object"
    ]

    extra = obs[
        "extra_element_properties"
    ]

    candidates = []
    seen = set()

    interactive_roles = {
        "button",
        "link",
        "checkbox",
        "radio",
        "combobox",
        "menuitem",
        "option",
        "tab",
        "textbox",
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

        if bid in seen:
            continue

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

        if visibility < 0.5:
            continue

        # For this first integration we expose all
        # elements that BrowserGym marks clickable,
        # plus known interactive AX roles.
        if (
            not clickable
            and
            role not in interactive_roles
        ):
            continue

        if not name:
            continue

        seen.add(
            bid
        )

        candidates.append({
            "bid": bid,
            "role": role,
            "name": name,
            "description":
                f'CLICK {role} "{name}"',
        })

    return candidates[
        :len(LETTERS)
    ]


def visible_axtree(
    obs,
):
    return (
        flatten_axtree_to_str(
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
    )


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

Choose the single available action that most directly satisfies the user's explicit goal.

Important rules:
- Choose only from the available actions.
- Match the requested UI element precisely.
- Prefer an action whose visible name directly matches the user's request.
- Do not choose unrelated controls.
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

    print()
    print("=" * 70)
    print(
        "OPENJEV + BROWSERGYM + MINIWOB"
    )
    print("=" * 70)

    print(
        "Task:",
        TASK,
    )

    print(
        "Seed:",
        SEED,
    )

    env = gym.make(
        TASK,
        headless=False,
    )

    record = {
        "task":
            TASK,
        "seed":
            SEED,
    }

    try:

        obs, info = env.reset(
            seed=SEED
        )

        goal = str(
            obs["goal"]
        )

        print()
        print("GOAL:")
        print(goal)

        print()
        print("URL:")
        print(
            obs["url"]
        )

        page_text = (
            visible_axtree(
                obs
            )
        )

        print()
        print(
            "===== ACCESSIBILITY TREE ====="
        )
        print(
            page_text
        )

        candidates = (
            collect_click_candidates(
                obs
            )
        )

        if not candidates:
            raise RuntimeError(
                "No actionable candidates found."
            )

        print()
        print(
            "===== CANDIDATE ACTIONS ====="
        )

        for i, candidate in enumerate(
            candidates
        ):

            print(
                f"{LETTERS[i]} = "
                f"{candidate['description']} "
                f"[bid={candidate['bid']}]"
            )

        (
            result,
            decision_latency,
            decision_context,
        ) = ask_openjev(
            goal,
            page_text,
            candidates,
        )

        print()
        print(
            "===== OPENJEV RANKING ====="
        )

        ranked = sorted(
            result["options"],
            key=lambda x:
                x["probability"],
            reverse=True,
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
            "Decision latency:",
            f"{decision_latency * 1000:.1f} ms",
        )

        browsergym_action = (
            f'click("{chosen["bid"]}")'
        )

        print()
        print(
            "EXECUTING BROWSERGYM ACTION:"
        )
        print(
            browsergym_action
        )

        (
            obs2,
            reward,
            terminated,
            truncated,
            info2,
        ) = env.step(
            browsergym_action
        )

        task_info = (
            info2.get(
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

        print()
        print(
            "===== OFFICIAL ENV RESULT ====="
        )

        print(
            "BrowserGym reward:",
            reward,
        )

        print(
            "RAW_REWARD_GLOBAL:",
            raw_reward,
        )

        print(
            "REWARD_REASON:",
            reward_reason,
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
            obs2.get(
                "last_action_error"
            ),
        )

        # For click-button this should be
        # a full positive completion.
        success = (
            float(reward) > 0
            and
            bool(terminated)
            and
            not bool(
                obs2.get(
                    "last_action_error"
                )
            )
        )

        record.update({
            "goal":
                goal,
            "url":
                str(obs["url"]),
            "axtree":
                page_text,
            "candidates":
                candidates,
            "openjev_response":
                result,
            "decision_latency_s":
                decision_latency,
            "chosen_letter":
                best_letter,
            "chosen_candidate":
                chosen,
            "browsergym_action":
                browsergym_action,
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
                str(
                    obs2.get(
                        "last_action_error",
                        "",
                    )
                ),
            "success":
                success,
        })

        print()
        print("=" * 70)

        if success:
            print(
                "MINIWOB_OPENJEV_CLICK_BUTTON=PASS"
            )
        else:
            print(
                "MINIWOB_OPENJEV_CLICK_BUTTON=FAIL"
            )

        print("=" * 70)

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

        output = (
            RESULTS_DIR
            / (
                "miniwob_openjev_"
                "click_button_"
                f"seed{SEED}_"
                f"{int(time.time())}.json"
            )
        )

        output.write_text(
            json.dumps(
                record,
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
