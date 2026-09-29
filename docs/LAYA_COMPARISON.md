# OpenJEV + Gemma 3 4B vs Laya-browser v17s

## Objective

This experiment compares the existing local Jev-style browser-control system against the browser-tuned Laya model while keeping the BrowserGym environment, MiniWoB tasks, seeds, candidate-generation layer and browser execution layer fixed.

The two decision approaches are:

- OpenJEV + Gemma 3 4B: a general instruction model used as a bounded Jev-style scorer.
- Laya-browser v17s: a browser-tuned decision model using typed operation and target decisions.

Laya model source:
https://huggingface.co/cklxx/laya-browser

Pinned revision:
ac29aefbc3a9b541f270e122e2e36d7e7081adaa

The exact revision is also stored in LAYA_BROWSER_COMMIT.txt.

## Evaluation protocol

The controlled Core-9 suite contains:

- click-button
- click-link
- enter-text
- choose-list
- click-checkboxes
- click-option
- click-menu
- click-dialog
- navigate-tree

Each task was evaluated with seeds 0 through 9.

That gives 90 episodes per system.

Both systems used the same local Apple M2 Pro machine, BrowserGym environment, MiniWoB++ source, task seeds, candidate-generation harness and browser-action execution layer.

Only the decision engine changed.

## Core-9 success results

| Task | OpenJEV + Gemma 3 4B | Laya-browser v17s |
| --- | ---: | ---: |
| click-button | 10/10 | 10/10 |
| click-link | 3/10 | 3/10 |
| enter-text | 10/10 | 10/10 |
| choose-list | 10/10 | 10/10 |
| click-checkboxes | 3/10 | 3/10 |
| click-option | 4/10 | 7/10 |
| click-menu | 2/10 | 2/10 |
| click-dialog | 0/10 | 10/10 |
| navigate-tree | 4/10 | 5/10 |
| Overall | 46/90 (51.11%) | 60/90 (66.67%) |

Observed difference:

- 14 additional successful episodes for Laya.
- 15.56 percentage-point absolute success-rate increase.
- Approximately 30.4% more successful episodes relative to the OpenJEV baseline.

## Decision latency

| Metric | OpenJEV + Gemma 3 4B | Laya-browser v17s |
| --- | ---: | ---: |
| Model decisions | 380 | 259 |
| Deterministic selections | 11 | 11 |
| Mean | 1320.4 ms | 170.4 ms |
| Median | 1149.7 ms | 167.5 ms |
| P95 | 1793.1 ms | 230.6 ms |
| Minimum | 920.5 ms | 111.1 ms |
| Maximum | 4295.2 ms | 310.1 ms |

On this local setup, mean observed decision latency was approximately 7.75x lower for Laya.

Median latency was approximately 6.86x lower and P95 latency approximately 7.78x lower.

These numbers describe observed system decision latency on this machine. They should not be interpreted as hardware-independent model latency.

## Enter-text validation

Before the broad Core-9 run, Laya was evaluated on browsergym/miniwob.enter-text using seeds 0 through 9.

Laya result:

- Success: 10/10
- Mean model-decision latency: 189.93 ms
- Median: 192.65 ms
- Min/max: 165.8 / 206.1 ms

The existing OpenJEV enter-text run also achieved 10/10, with approximately 804.4 ms mean model-decision latency.

This provided an initial same-task validation before the broad evaluation.

## Failure analysis

### click-dialog

This produced the largest difference.

OpenJEV: 0/10

Laya: 10/10

In inspected OpenJEV failures, the scorer repeatedly selected the same incorrect clickable element until the step budget was exhausted.

Laya selected the dialog close target and completed the task.

This task alone contributed 10 of the 14 net additional successful Laya episodes.

### click-option

OpenJEV: 4/10

Laya: 7/10

Laya produced a net improvement of three successful episodes, although there were individual seeds where OpenJEV succeeded and Laya failed.

### navigate-tree

OpenJEV: 4/10

Laya: 5/10

In one inspected case the requested item was represented in the browser state. OpenJEV selected the wrong candidate and terminated unsuccessfully, while Laya selected the successful target.

### click-link

Both systems achieved 3/10.

A major limitation appears in the candidate representation. The accessibility state contains useful visible text, but several clickable candidates are reduced to descriptions such as:

CLICK generic "unnamed generic"

This removes semantic information before the bounded decision step.

Different seeds therefore produced opposite outcomes between the two models.

### click-checkboxes

Both systems achieved 3/10.

OpenJEV sometimes submitted before all required checkboxes were selected.

Laya often selected required checkboxes correctly, but some failures showed it clicking an already-selected checkbox again and toggling it back off.

This exposes a state-awareness limitation in the shared candidate layer.

A future candidate generator should avoid proposing actions that undo an already-satisfied state.

## Interpretation

Within this controlled evaluation, browser-tuned Laya achieved higher task success and substantially lower observed decision latency than OpenJEV + Gemma 3 4B.

The improvement was not uniform across every task family. Most of the net success gain came from dialog interaction, with smaller gains in click-option and navigate-tree.

The remaining failures show that model choice is not the only bottleneck.

Candidate semantics and state-aware candidate filtering materially affect browser-control performance.

## Architecture takeaway

OpenJEV path:

General-purpose Gemma 3 4B instruction model
+ Jev-style bounded scoring
+ prompt-driven decision policy

Laya path:

Browser-tuned Laya decision model
+ typed operation and target decisions
+ browser-specific training

For this controlled Core-9 evaluation, the browser-tuned decision model produced the stronger result.

## Scope and limitations

This experiment does not claim that:

- Laya universally outperforms OpenJEV.
- 66.67% is a full MiniWoB benchmark score.
- The latency ratio transfers unchanged to other hardware.
- The two inference implementations are identical.
- The current candidate-generation layer is optimal.

The result is specifically a project-controlled MiniWoB Core-9 comparison.

## Reproduction

Laya decision adapter:

benchmark/laya_decider.py

Laya MiniWoB runner:

benchmark/miniwob_laya_agent_v1.py

Pinned model revision:

LAYA_BROWSER_COMMIT.txt

Machine-readable comparison:

results/laya_vs_openjev_core9_summary.json

Raw local benchmark logs and downloaded model weights remain excluded from version control.
