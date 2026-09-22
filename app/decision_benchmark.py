import argparse
import csv
import json
import math
import statistics
import time
from pathlib import Path

import httpx


LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent

CASES_PATH = (
    ROOT_DIR
    / "benchmark"
    / "decision_cases_v1.json"
)

RESULTS_DIR = (
    ROOT_DIR
    / "benchmark"
    / "results"
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

MODEL_PATH = (
    ROOT_DIR
    / "third_party"
    / "open-jev"
    / "models"
    / "gemma-3-4b-it"
)

OPENJEV_URL = (
    "http://127.0.0.1:8000/score"
)


def label(index):
    return LETTERS[index]


def rotate(items, amount):
    amount %= len(items)

    return (
        items[amount:]
        + items[:amount]
    )


def build_prompt(
    case,
    actions,
):
    menu = "\n".join(
        f"{label(i)}. {action}"
        for i, action
        in enumerate(actions)
    )

    return f"""You are controlling a web browser.

User goal:
{case["goal"]}

Current page title:
{case["page_title"]}

Current visible page text:
{case["visible_text"]}

Available actions:
{menu}

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

Respond with ONLY the corresponding single letter.
Do not explain your answer."""


def percentile(values, p):
    ordered = sorted(values)

    if not ordered:
        return None

    index = (
        math.ceil(
            p * len(ordered)
        )
        - 1
    )

    index = max(
        0,
        min(
            index,
            len(ordered) - 1,
        ),
    )

    return ordered[index]


def jev_warmup(client):
    payload = {
        "context": (
            "Choose the correct option.\n"
            "A. Correct\n"
            "B. Wrong\n"
            "Answer:"
        ),
        "options": [
            "A",
            "B",
        ],
        "norm": "pmi",
        "chat": True,
        "sep": "",
    }

    started = time.perf_counter()

    response = client.post(
        OPENJEV_URL,
        json=payload,
    )

    response.raise_for_status()

    return (
        time.perf_counter()
        - started
    )


def jev_decide(
    client,
    prompt,
    number_of_actions,
):
    options = [
        label(i)
        for i in range(
            number_of_actions
        )
    ]

    payload = {
        "context": prompt,
        "options": options,
        "norm": "pmi",
        "chat": True,
        "sep": "",
    }

    started = time.perf_counter()

    response = client.post(
        OPENJEV_URL,
        json=payload,
    )

    response.raise_for_status()

    latency = (
        time.perf_counter()
        - started
    )

    result = response.json()

    predicted_index = (
        result["best_index"]
    )

    predicted_letter = label(
        predicted_index
    )

    ranked = sorted(
        result["options"],
        key=lambda x:
            x["probability"],
        reverse=True,
    )

    top1_probability = (
        ranked[0]["probability"]
    )

    if len(ranked) >= 2:
        margin = (
            ranked[0]["probability"]
            - ranked[1]["probability"]
        )
    else:
        margin = None

    return {
        "predicted_letter":
            predicted_letter,
        "valid_output":
            True,
        "format_violation":
            False,
        "raw_output":
            predicted_letter,
        "latency_s":
            latency,
        "top1_probability":
            top1_probability,
        "top1_margin":
            margin,
    }


def load_generative():
    from mlx_lm import (
        load,
        generate,
    )

    from mlx_lm.sample_utils import (
        make_sampler,
    )

    model, tokenizer = load(
        str(MODEL_PATH)
    )

    return (
        model,
        tokenizer,
        generate,
        make_sampler,
    )


def generative_warmup(
    model,
    tokenizer,
    generate,
    make_sampler,
):
    messages = [{
        "role": "user",
        "content": (
            "Choose one option.\n"
            "A. Correct\n"
            "B. Wrong\n"
            "Respond with only A or B."
        ),
    }]

    prompt = (
        tokenizer
        .apply_chat_template(
            messages,
            add_generation_prompt=True,
        )
    )

    started = time.perf_counter()

    generate(
        model=model,
        tokenizer=tokenizer,
        prompt=prompt,
        max_tokens=1,
        sampler=make_sampler(
            temp=0.0
        ),
        verbose=False,
    )

    return (
        time.perf_counter()
        - started
    )


def generative_decide(
    model,
    tokenizer,
    generate,
    make_sampler,
    prompt,
    number_of_actions,
):
    messages = [{
        "role": "user",
        "content": prompt,
    }]

    formatted = (
        tokenizer
        .apply_chat_template(
            messages,
            add_generation_prompt=True,
        )
    )

    started = time.perf_counter()

    raw = generate(
        model=model,
        tokenizer=tokenizer,
        prompt=formatted,
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

    stripped = (
        raw.strip().upper()
    )

    allowed = LETTERS[
        :number_of_actions
    ]

    valid = (
        len(stripped) == 1
        and
        stripped in allowed
    )

    predicted = (
        stripped
        if valid
        else None
    )

    return {
        "predicted_letter":
            predicted,
        "valid_output":
            valid,
        "format_violation":
            not valid,
        "raw_output":
            raw,
        "latency_s":
            latency,
        "top1_probability":
            None,
        "top1_margin":
            None,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mode",
        required=True,
        choices=[
            "jev",
            "generative",
        ],
    )

    parser.add_argument(
        "--repeats",
        type=int,
        default=4,
    )

    args = parser.parse_args()

    cases = json.loads(
        CASES_PATH.read_text()
    )

    print()
    print("=" * 70)
    print(
        "DECISION BENCHMARK"
    )
    print("=" * 70)

    print(
        "Mode    :",
        args.mode,
    )

    print(
        "Cases   :",
        len(cases),
    )

    print(
        "Repeats :",
        args.repeats,
    )

    print(
        "Total   :",
        len(cases)
        * args.repeats,
    )

    records = []

    client = None
    model = None
    tokenizer = None
    generate = None
    make_sampler = None

    if args.mode == "jev":

        client = httpx.Client(
            timeout=60.0
        )

        print()
        print(
            "Warming OpenJEV..."
        )

        warmup_s = (
            jev_warmup(
                client
            )
        )

    else:

        print()
        print(
            "Loading Gemma..."
        )

        load_start = (
            time.perf_counter()
        )

        (
            model,
            tokenizer,
            generate,
            make_sampler,
        ) = load_generative()

        model_load_s = (
            time.perf_counter()
            - load_start
        )

        print(
            "Model load:",
            f"{model_load_s:.2f}s",
        )

        print(
            "Warming generation..."
        )

        warmup_s = (
            generative_warmup(
                model,
                tokenizer,
                generate,
                make_sampler,
            )
        )

    print(
        "Warm-up:",
        f"{warmup_s * 1000:.1f} ms",
    )

    for repeat in range(
        args.repeats
    ):

        print()
        print(
            f"===== ROTATION "
            f"{repeat} ====="
        )

        for case in cases:

            actions = rotate(
                case["actions"],
                repeat,
            )

            expected_index = (
                actions.index(
                    case[
                        "expected_action"
                    ]
                )
            )

            expected_letter = (
                label(
                    expected_index
                )
            )

            prompt = build_prompt(
                case,
                actions,
            )

            if args.mode == "jev":

                decision = (
                    jev_decide(
                        client,
                        prompt,
                        len(actions),
                    )
                )

            else:

                decision = (
                    generative_decide(
                        model,
                        tokenizer,
                        generate,
                        make_sampler,
                        prompt,
                        len(actions),
                    )
                )

            predicted_letter = (
                decision[
                    "predicted_letter"
                ]
            )

            correct = (
                predicted_letter
                == expected_letter
            )

            predicted_action = None

            if predicted_letter:
                predicted_index = (
                    LETTERS.index(
                        predicted_letter
                    )
                )

                if (
                    predicted_index
                    < len(actions)
                ):
                    predicted_action = (
                        actions[
                            predicted_index
                        ]
                    )

            record = {
                "mode":
                    args.mode,
                "case_id":
                    case["id"],
                "rotation":
                    repeat,
                "goal":
                    case["goal"],
                "actions":
                    actions,
                "expected_action":
                    case[
                        "expected_action"
                    ],
                "expected_letter":
                    expected_letter,
                "predicted_letter":
                    predicted_letter,
                "predicted_action":
                    predicted_action,
                "correct":
                    correct,
                "valid_output":
                    decision[
                        "valid_output"
                    ],
                "format_violation":
                    decision[
                        "format_violation"
                    ],
                "raw_output":
                    decision[
                        "raw_output"
                    ],
                "latency_s":
                    decision[
                        "latency_s"
                    ],
                "top1_probability":
                    decision[
                        "top1_probability"
                    ],
                "top1_margin":
                    decision[
                        "top1_margin"
                    ],
            }

            records.append(
                record
            )

            marker = (
                "PASS"
                if correct
                else "FAIL"
            )

            print(
                f"{marker:4} "
                f"{case['id']:<28} "
                f"expected={expected_letter} "
                f"predicted="
                f"{predicted_letter} "
                f"latency="
                f"{decision['latency_s'] * 1000:.1f}ms"
            )

            if not correct:

                print(
                    "     expected:",
                    case[
                        "expected_action"
                    ],
                )

                print(
                    "     predicted:",
                    predicted_action,
                )

    if client is not None:
        client.close()

    total = len(records)

    correct_count = sum(
        1
        for record in records
        if record["correct"]
    )

    invalid_count = sum(
        1
        for record in records
        if not record[
            "valid_output"
        ]
    )

    format_count = sum(
        1
        for record in records
        if record[
            "format_violation"
        ]
    )

    latencies_ms = [
        record["latency_s"]
        * 1000
        for record in records
    ]

    accuracy = (
        correct_count
        / total
        if total
        else 0.0
    )

    summary = {
        "mode":
            args.mode,
        "cases":
            len(cases),
        "repeats":
            args.repeats,
        "total_decisions":
            total,
        "correct":
            correct_count,
        "accuracy":
            accuracy,
        "invalid_outputs":
            invalid_count,
        "format_violations":
            format_count,
        "latency_ms_mean":
            statistics.mean(
                latencies_ms
            ),
        "latency_ms_median":
            statistics.median(
                latencies_ms
            ),
        "latency_ms_p95":
            percentile(
                latencies_ms,
                0.95,
            ),
        "warmup_ms":
            warmup_s * 1000,
    }

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(
        "Mode:",
        args.mode,
    )

    print(
        "Accuracy:",
        f"{correct_count}/{total}",
        f"({accuracy * 100:.2f}%)",
    )

    print(
        "Invalid outputs:",
        invalid_count,
    )

    print(
        "Format violations:",
        format_count,
    )

    print(
        "Latency mean:",
        f"{summary['latency_ms_mean']:.1f} ms",
    )

    print(
        "Latency median:",
        f"{summary['latency_ms_median']:.1f} ms",
    )

    print(
        "Latency p95:",
        f"{summary['latency_ms_p95']:.1f} ms",
    )

    timestamp = int(
        time.time()
    )

    base = (
        RESULTS_DIR
        / (
            f"{args.mode}_"
            f"decision_benchmark_"
            f"{timestamp}"
        )
    )

    json_path = Path(
        str(base) + ".json"
    )

    csv_path = Path(
        str(base) + ".csv"
    )

    json_path.write_text(
        json.dumps(
            {
                "summary":
                    summary,
                "records":
                    records,
            },
            indent=2,
        )
    )

    with csv_path.open(
        "w",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "mode",
                "case_id",
                "rotation",
                "expected_letter",
                "predicted_letter",
                "correct",
                "valid_output",
                "format_violation",
                "latency_s",
                "top1_probability",
                "top1_margin",
                "expected_action",
                "predicted_action",
            ],
        )

        writer.writeheader()

        for record in records:

            writer.writerow({
                key:
                    record.get(key)
                for key
                in writer.fieldnames
            })

    print()
    print("JSON:")
    print(json_path)

    print()
    print("CSV:")
    print(csv_path)


if __name__ == "__main__":
    main()
