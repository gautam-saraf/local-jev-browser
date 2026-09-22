# Results

## Local Browser Experiments

| Experiment | Result |
|---|---:|
| Playwright browser smoke test | PASS |
| First OpenJEV browser click | PASS |
| Multi-step local navigation | PASS |
| Search + text entry | PASS |
| Real Wikipedia navigation | PASS |
| Real Playwright documentation navigation | PASS |
| MiniWoB click-button | PASS |
| MiniWoB enter-text 10 seeds | 10/10 |

## Controlled Decision Diagnostic

OpenJEV Chat + PMI:

- 52 / 56 correct
- 92.86% accuracy
- 0 invalid outputs
- 0 format violations
- Mean latency ~904.8 ms
- Median latency ~905.3 ms
- P95 latency ~951.8 ms

## MiniWoB enter-text

- 10 / 10 successful episodes
- 10 / 10 full raw reward
- 20 browser actions
- 10 actual OpenJEV decisions
- 10 deterministic selections
- ~804.4 ms mean OpenJEV decision latency

## MiniWoB Core-9

| Task | Result |
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
| OVERALL | 46/90 (51.11%) |

This was the first broad evaluation and was preserved without tuning against the failures.
