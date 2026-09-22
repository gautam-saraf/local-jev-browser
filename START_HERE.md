# Start Here

This repository is a research proof-of-concept for local browser control using
an open-weight model with Jev-style bounded action selection.

## What this project does

The system:

1. reads the browser state,
2. generates a bounded set of valid browser actions,
3. uses a local Gemma 3 4B model through OpenJEV-style scoring,
4. selects one action,
5. executes it using Playwright or BrowserGym,
6. repeats until the task is completed.

No cloud LLM is required for the browser decision loop.

## Important terminology

This project does NOT run the proprietary TypeSafe AI Jev model.

It uses:

- Gemma 3 4B locally
- the community OpenJEV implementation
- Playwright
- BrowserGym
- MiniWoB++

The correct description is:

"Jev-style local browser control using OpenJEV and Gemma 3 4B."

## Where to start

If you want to understand the project:

- README.md
- RESULTS.md
- START_HERE.md

If you want to inspect the main local browser agent:

- app/browser_agent_v2.py

If you want to inspect the real-site experiments:

- app/browser_agent_v3_wikipedia.py
- app/browser_agent_v4_playwright.py

If you want to inspect the current standardized benchmark agent:

- benchmark/miniwob_jev_agent_broad_v1.py

If you want to see benchmark results:

- RESULTS.md
- results/miniwob_core9_summary.json
- results/miniwob_enter_text_openjev_10seed_summary.json

## Experimental files

Several Python files are intentionally preserved because this repository also
records the evolution of the experiment.

They are not different production applications.

Examples include:

- early browser-control prototypes,
- SUM-scoring baselines,
- Chat+PMI experiments,
- generative baselines,
- diagnostic scripts,
- standardized benchmark runners.

The recommended current benchmark implementation is:

benchmark/miniwob_jev_agent_broad_v1.py

## External dependencies

Large third-party repositories and model weights are intentionally NOT stored
inside this Git repository.

OpenJEV is obtained from:

https://github.com/daseinlabs/open-jev

MiniWoB++ is obtained from:

https://github.com/Farama-Foundation/miniwob-plusplus

Gemma model:

google/gemma-3-4b-it

The exact OpenJEV revision used in the experiment is recorded in:

OPENJEV_COMMIT.txt

The MiniWoB++ revision used in the experiment is:

7fd85d71a4b60325c6585396ec4f48377d049838

## Current results

Controlled bounded-action diagnostic:

52 / 56 correct = 92.86%

MiniWoB enter-text:

10 / 10 successful seeded episodes

MiniWoB Core-9 representative evaluation:

46 / 90 successful episodes = 51.11%

The broader MiniWoB result is intentionally preserved with failures and shows
where the current candidate-action generator still needs improvement.

## Project status

Research POC.

The next repository-cleanup steps will add:

- a reproducible setup guide,
- architecture documentation,
- third-party dependency documentation,
- one-command demo scripts,
- benchmark run scripts.
