# Quick Start

This guide explains how to reproduce and run the local browser-control POC from a clean checkout.

## 1. Prerequisites

Recommended environment:

- Apple Silicon Mac
- 16 GB or more unified memory
- Python 3.12
- Git
- uv
- Google Chrome
- Hugging Face account with access to google/gemma-3-4b-it

The original experiment was developed on an Apple M2 Pro with 32 GB unified memory.

## 2. Clone this repository

    git clone <repository-url>
    cd local-jev-browser

## 3. External components

This repository intentionally does not include large third-party repositories or model weights.

The experiment depends on:

- OpenJEV
- MiniWoB++
- Gemma 3 4B

The exact revisions used are recorded in:

- OPENJEV_COMMIT.txt
- MINIWOB_COMMIT.txt

## 4. Clone OpenJEV

    mkdir -p third_party
    git clone https://github.com/daseinlabs/open-jev.git third_party/open-jev
    cd third_party/open-jev
    git checkout $(cat ../../OPENJEV_COMMIT.txt)

Create the OpenJEV environment:

    uv sync --extra torch

## 5. Download Gemma 3 4B

Make sure your Hugging Face account has access to:

    google/gemma-3-4b-it

Authenticate:

    .venv/bin/hf auth login

Download the model:

    .venv/bin/hf download google/gemma-3-4b-it --local-dir models/gemma-3-4b-it

## 6. Clone MiniWoB++

Return to the project root:

    cd ../..

Clone MiniWoB++:

    git clone https://github.com/Farama-Foundation/miniwob-plusplus.git third_party/miniwob-plusplus
    cd third_party/miniwob-plusplus
    git checkout $(cat ../../MINIWOB_COMMIT.txt)
    cd ../..

## 7. Create the application environment

    uv venv --python 3.12 app/.venv

Install application dependencies:

    uv pip install --python app/.venv/bin/python -r requirements/app.txt

## 8. Create the benchmark environment

    uv venv --python 3.12 benchmark/.venv

Install benchmark dependencies:

    uv pip install --python benchmark/.venv/bin/python -r requirements/benchmark.txt

Install Playwright Chromium:

    benchmark/.venv/bin/python -m playwright install chromium

## 9. Start OpenJEV

Open Terminal 1:

    cd third_party/open-jev
    make serve

Keep this terminal running.

The scoring endpoint should be available at:

    http://127.0.0.1:8000/score

## 10. Run the main local browser demo

Open Terminal 2 from the project root:

    app/.venv/bin/python app/browser_agent_v2.py

This is the recommended local reproducible browser-control demonstration.

## 11. Run real-site demonstrations

Wikipedia:

    app/.venv/bin/python app/browser_agent_v3_wikipedia.py

Playwright documentation:

    app/.venv/bin/python app/browser_agent_v4_playwright.py

Real websites can change over time, so these should be treated as demonstrations rather than fixed benchmark results.

## 12. Run MiniWoB

Load the MiniWoB path:

    source benchmark/miniwob_env.sh

Example standardized episode:

    benchmark/.venv/bin/python benchmark/miniwob_jev_agent_broad_v1.py --task browsergym/miniwob.enter-text --seed 42 --max-steps 12 --headless

## 13. Important terminology

This project does not run the proprietary TypeSafe AI Jev model.

The correct description is:

    Jev-style local browser control using the community OpenJEV implementation and Gemma 3 4B.

## 14. Results

See:

- RESULTS.md
- results/miniwob_core9_summary.json
- results/miniwob_enter_text_openjev_10seed_summary.json

## 15. Recommended reading order

1. START_HERE.md
2. README.md
3. QUICKSTART.md
4. RESULTS.md
5. benchmark/ and app/ only if implementation details are needed
