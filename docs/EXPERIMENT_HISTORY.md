# Experiment History

This repository intentionally preserves several Python files because they document the evolution of the research POC.

They are not separate production applications.

## Browser-control progression

- `app/browser_smoke.py` - initial Playwright validation
- `app/jev_browser_step.py` - first OpenJEV-selected browser action
- `app/jev_browser_loop.py` - first multi-step bounded browser loop
- `app/browser_agent_v2.py` - main local search and navigation demo
- `app/browser_agent_v3_wikipedia.py` - real Wikipedia experiment
- `app/browser_agent_v4_playwright.py` - real Playwright documentation experiment

## Decision-scoring experiments

- `app/browser_agent_v2_sum_baseline.py` - earlier SUM-scoring baseline
- `app/diagnose_installation_decision.py` - focused semantic decision diagnostic
- `app/decision_benchmark.py` - controlled 56-decision diagnostic

## Generative comparison

- `app/generative_agent_v1.py` - JSON-output generative baseline
- `app/generative_letter_agent_v2.py` - weak-prompt single-letter baseline
- `app/generative_letter_agent_v3_goalfocused.py` - goal-focused single-letter baseline
- `app/generative_letter_diagnostic.py` - isolated generative diagnostic

The goal-focused generative baseline also completed the target workflow, so the project does not claim that bounded scoring succeeds simply because normal generation cannot.

## Standardized benchmark progression

- `benchmark/miniwob_smoke.py` - BrowserGym environment validation
- `benchmark/miniwob_jev_click_button.py` - first standardized MiniWoB episode
- `benchmark/miniwob_jev_agent_v1.py` - initial generic agent
- `benchmark/miniwob_jev_agent_v2.py` - intermediate broader agent
- `benchmark/miniwob_jev_agent_broad_v1.py` - current broad MiniWoB implementation

## Recommended entry points

For normal use, start from the repository root:

    make verify
    make serve
    make demo
    make miniwob

Do not select historical Python files unless reviewing the experiment progression.
