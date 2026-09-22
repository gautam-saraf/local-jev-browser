# Local Open-Weight Browser Control with Jev-Style Bounded Decisions

Research POC for controlling a browser using a fully local open-weight model and bounded candidate-action scoring.

## Important Note

This project does not run the proprietary TypeSafe AI Jev model.

It explores a Jev-like bounded-decision architecture using:

- Gemma 3 4B
- community OpenJEV
- MLX / MLX-LM
- Playwright
- BrowserGym
- MiniWoB++

## Architecture

User Goal
    ↓
Browser Observation / Accessibility Tree
    ↓
Candidate Action Generator
    ↓
Bounded Actions: A / B / C / ...
    ↓
Local Gemma 3 4B + OpenJEV Chat/PMI
    ↓
Selected Browser Action
    ↓
Playwright / BrowserGym
    ↓
Browser Execution
    ↓
Environment Reward / Next State

## What Was Demonstrated

- Local open-weight browser control
- Multi-step navigation
- Search
- Text entry
- Dropdown selection
- Real Wikipedia navigation
- Real Playwright documentation navigation
- BrowserGym / MiniWoB standardized evaluation

## Controlled Decision Benchmark

14 decision cases were evaluated with four action-order rotations.

Total decisions: 56

Results:

- Correct: 52 / 56
- Accuracy: 92.86%
- Invalid outputs: 0
- Format violations: 0
- Mean latency: ~904.8 ms
- Median latency: ~905.3 ms
- P95 latency: ~951.8 ms

This is an internal decision diagnostic and not a full external browser benchmark.

## MiniWoB enter-text

10 seeded episodes:

- Success: 10 / 10
- Full raw reward: 10 / 10
- Total browser actions: 20
- Actual OpenJEV model decisions: 10
- Deterministic single-candidate actions: 10
- Mean model-decision latency: ~804.4 ms

## MiniWoB Core-9

Representative evaluation:

| Task | Success |
|---|---:|
| click-button | 10/10 |
| click-link | 3/10 |
| enter-text | 10/10 |
| choose-list | 10/10 |
| click-checkboxes | 3/10 |
| click-option | 4/10 |
| click-menu | 2/10 |
| click-dialog | 0/10 |
| navigate-tree | 4/10 |
| Overall | 46/90 (51.11%) |

The failures are intentionally preserved.

The current controller performs strongly on basic forms, direct clicking and dropdown selection, but richer menus, dialogs, checkbox state management and hierarchical navigation require additional work.

## Generative Baseline Finding

The same Gemma 3 4B model was also tested with normal autoregressive generation.

A weakly constrained generative baseline failed a controlled navigation workflow.

A goal-focused single-letter generative baseline successfully completed the same workflow.

Therefore this project does not claim that Jev-style scoring is universally superior to normal LLM generation.

The research question is instead around:

- bounded action guarantees
- semantic decision quality
- robustness
- option-order sensitivity
- invalid actions
- latency
- recovery

## Repository Structure

app/
- browser-control experiments
- local demo sites
- generative baselines
- real-site agents

benchmark/
- BrowserGym / MiniWoB agents
- benchmark runners
- task inspection utilities

experiments/
- decision diagnostics

results/
- selected compact benchmark results

environment/
- dependency snapshots

docs/
- reproducibility notes

## Model Weights

Gemma model weights are not stored in this repository.

Model used:

google/gemma-3-4b-it

## Status

Research POC.

Not a production browser-control system.
