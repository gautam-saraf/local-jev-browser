import json
import os
import time
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]

LAYA_URL = os.environ.get(
    "LAYA_SYSTEMONE_URL",
    "http://127.0.0.1:8791/v1/systemone",
)

SAMPLE_REQUEST = (
    ROOT
    / "third_party"
    / "laya-browser"
    / "code"
    / "sample_request.json"
)

_SAMPLE = json.loads(
    SAMPLE_REQUEST.read_text()
)

BASE_RULES = (
    _SAMPLE["questions"]["operation"]
    ["instructions"]["rules"]
)

_TARGET_RULES = (
    _SAMPLE["questions"]["click_target"]
    ["instructions"]["rules"]
)

if isinstance(_TARGET_RULES, list):
    TARGET_RULE = _TARGET_RULES[-1]
else:
    TARGET_RULE = str(_TARGET_RULES)


RECENT_ACTIONS = []


TYPE_TO_OPERATION = {
    "click": "CLICK",
    "fill": "TYPE_TEXT",
    "select_option": "SELECT",
}


OP_DESCRIPTIONS = {
    "CLICK":
        "Click one of the offered visible elements.",
    "TYPE_TEXT":
        "Enter the goal-required text into an offered editable field.",
    "SELECT":
        "Select the goal-required value from an offered dropdown.",
}


def target_description(
    index,
    candidate,
):
    role = (
        candidate.get("role")
        or "element"
    )

    name = (
        candidate.get("name")
        or f"unnamed {role}"
    )

    ctype = candidate.get("type")

    if ctype == "select_option":
        option = candidate.get(
            "text",
            "",
        )

        return (
            f"[{index}] "
            f"{name} -> {option}"
        )

    return (
        f"[{index}] "
        f"{name} ({role})"
    )


def build_laya_request(
    goal,
    page_text,
    candidates,
):
    grouped = {}

    for index, candidate in enumerate(
        candidates
    ):
        operation = TYPE_TO_OPERATION.get(
            candidate.get("type")
        )

        if operation is None:
            continue

        grouped.setdefault(
            operation,
            {},
        )

        grouped[operation][str(index)] = (
            target_description(
                index,
                candidate,
            )
        )

    if not grouped:
        raise RuntimeError(
            "No Laya-compatible candidates"
        )

    operation_criteria = {
        operation:
            OP_DESCRIPTIONS[operation]
        for operation in grouped
    }

    questions = {
        "operation": {
            "type": "choice",
            "instructions": {
                "goal": goal,
                "rules": BASE_RULES,
            },
            "criteria":
                operation_criteria,
        }
    }

    for operation, criteria in (
        grouped.items()
    ):
        question_id = (
            operation.lower()
            + "_target"
        )

        questions[question_id] = {
            "type": "choice",
            "instructions": {
                "goal": goal,
                "operation":
                    operation,
                "rules": [
                    BASE_RULES,
                    TARGET_RULE,
                ],
            },
            "criteria":
                criteria,
        }

    state = {
        "page": {
            "url":
                "miniwob://current",
            "title":
                "MiniWoB",
            "text":
                page_text,
        },
        "recent_actions":
            RECENT_ACTIONS[-8:],
    }

    return {
        "model":
            "laya-browser-v17s",
        "state":
            state,
        "questions":
            questions,
    }


def ask_laya(
    goal,
    page_text,
    candidates,
):
    letters = [
        chr(ord("A") + i)
        for i in range(
            len(candidates)
        )
    ]

    # Keep the exact same deterministic
    # single-candidate behaviour used by
    # our OpenJEV benchmark.
    if len(candidates) == 1:
        chosen = candidates[0]

        RECENT_ACTIONS.append(
            chosen["description"]
        )

        return (
            {
                "best":
                    "A",
                "best_index":
                    0,
                "options": [
                    {
                        "option":
                            "A",
                        "probability":
                            1.0,
                        "logprob_sum":
                            None,
                        "n_tokens":
                            0,
                    }
                ],
                "decision_source":
                    "single_candidate_autoselect",
                "laya_raw":
                    None,
            },
            0.0,
            "single candidate",
        )

    payload = build_laya_request(
        goal,
        page_text,
        candidates,
    )

    started = time.perf_counter()

    response = httpx.post(
        LAYA_URL,
        json=payload,
        timeout=120.0,
    )

    response.raise_for_status()

    latency = (
        time.perf_counter()
        - started
    )

    raw = response.json()

    answers = raw["answers"]

    operation_answer = (
        answers["operation"]
    )

    operation = (
        operation_answer["choice"]
    )

    target_question = (
        operation.lower()
        + "_target"
    )

    if target_question not in answers:
        raise RuntimeError(
            "Laya selected operation "
            f"{operation!r} but returned "
            "no matching target answer. "
            f"Available answers: "
            f"{list(answers)}"
        )

    target_answer = (
        answers[target_question]
    )

    target_key = str(
        target_answer["choice"]
    )

    try:
        best_index = int(
            target_key
        )
    except ValueError as exc:
        raise RuntimeError(
            "Laya target was not one "
            f"of our candidate indexes: "
            f"{target_key!r}"
        ) from exc

    if (
        best_index < 0
        or best_index
        >= len(candidates)
    ):
        raise RuntimeError(
            "Laya returned candidate "
            f"index {best_index}, but "
            f"there are only "
            f"{len(candidates)} candidates."
        )

    chosen = candidates[
        best_index
    ]

    expected_operation = (
        TYPE_TO_OPERATION.get(
            chosen.get("type")
        )
    )

    if (
        expected_operation
        != operation
    ):
        raise RuntimeError(
            "Laya operation/target "
            "mismatch: operation="
            f"{operation}, candidate="
            f"{chosen}"
        )

    RECENT_ACTIONS.append(
        chosen["description"]
    )

    # Compatibility structure for the
    # existing benchmark main loop.
    # These candidate probabilities are
    # intentionally one-hot; the actual
    # Laya operation/target confidences
    # remain in laya_raw.
    options = []

    for i, letter in enumerate(
        letters
    ):
        options.append({
            "option":
                letter,
            "probability":
                1.0
                if i == best_index
                else 0.0,
            "logprob_sum":
                None,
            "n_tokens":
                0,
        })

    result = {
        "best":
            letters[best_index],
        "best_index":
            best_index,
        "options":
            options,
        "decision_source":
            "laya_browser_v17s_systemone",
        "laya_operation":
            operation,
        "laya_operation_confidence":
            operation_answer.get(
                "confidence"
            ),
        "laya_target":
            target_key,
        "laya_target_confidence":
            target_answer.get(
                "confidence"
            ),
        "laya_raw":
            raw,
        "probability_note":
            (
                "options[] is a compatibility "
                "one-hot view only; use the "
                "Laya operation/target "
                "confidences above."
            ),
    }

    context = json.dumps(
        payload,
        ensure_ascii=False,
    )

    return (
        result,
        latency,
        context,
    )
