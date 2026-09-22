# Architecture

## 1. Objective

This proof-of-concept evaluates whether a fully local open-weight language model can control a browser through a bounded decision interface.

The system separates four responsibilities:

1. Browser observation
2. Candidate action generation
3. Model-based action ranking
4. Deterministic browser execution

The language model is not given unrestricted authority to generate arbitrary browser commands.

---

## 2. High-Level Architecture

    User Goal
        |
        v
    Browser State
    DOM / Accessibility Tree
        |
        v
    Candidate Action Generator
        |
        |-- A = CLICK(...)
        |-- B = FILL(...)
        |-- C = SELECT(...)
        |
        v
    Local Gemma 3 4B
    OpenJEV Chat + PMI
        |
        v
    Selected Bounded Action
        |
        v
    Playwright / BrowserGym
        |
        v
    Browser Execution
        |
        v
    Updated Browser State
        |
        +---- repeat until completion

---

## 3. Model Layer

The decision model used in the experiment is:

    google/gemma-3-4b-it

The model runs locally on Apple Silicon through MLX / MLX-LM.

No cloud LLM is required for the browser decision loop.

---

## 4. Jev, OpenJEV and Jev-Style

These terms should not be confused.

### Jev

Jev refers to the proprietary TypeSafe AI system.

This repository does not contain or run the proprietary Jev model.

### OpenJEV

OpenJEV is the community implementation used in this experiment.

It provides local bounded option scoring over the Gemma model.

### Jev-style

Jev-style refers to the architectural idea explored here:

    define allowed decisions first
        |
        v
    score those bounded decisions
        |
        v
    execute only the selected legal action

The project should therefore be described as:

    Jev-style local browser control using OpenJEV and Gemma 3 4B.

---

## 5. Browser Observation

The browser is converted into structured state using DOM and accessibility information.

Typical information includes:

- element role
- accessible name
- element value
- browser element identifier
- visibility
- clickability

Example browser state:

    textbox value=""
    button "Submit"
    combobox value="Montenegro"

The controller converts this browser state into candidate actions.

---

## 6. Candidate Actions

Instead of allowing the model to freely generate arbitrary browser code, the controller constructs a bounded set of actions.

Example:

    A = FILL textbox with "Ashlea"
    B = CLICK button "Submit"

Another example:

    A = SELECT "Pitcairn"
    B = SELECT "Seychelles"
    C = SELECT "Croatia"
    D = CLICK "Submit"

The model only decides between the available candidates.

---

## 7. Decision Scoring

Early experiments used naive likelihood scoring.

A documentation-navigation test exposed a strong language prior.

The requested destination was:

    Installation

but naive scoring preferred:

    Introduction

Prompt changes alone did not reliably solve the issue.

Later experiments used:

    chat = true
    normalization = PMI
    candidate labels = A, B, C, ...

This configuration performed substantially better on the targeted diagnostic and subsequent browser workflow.

The displayed softmax values are ranking scores and should not be interpreted as calibrated confidence probabilities.

---

## 8. Browser Execution

Two browser execution layers were used.

### Playwright

Used for:

- local browser demonstrations
- real Wikipedia experiment
- real Playwright documentation experiment

### BrowserGym

Used for standardized MiniWoB evaluation.

Example BrowserGym actions:

    click("15")
    fill("14", "Ashlea")
    select_option("13", "Croatia")

The execution layer is separate from the language model.

---

## 9. Agent Loop

The agent repeatedly performs:

    observe browser
        |
        v
    construct valid actions
        |
        v
    rank actions
        |
        v
    execute selected action
        |
        v
    observe new state

The loop stops when:

- the task succeeds,
- the environment terminates,
- an unrecoverable condition occurs,
- or the maximum step limit is reached.

---

## 10. Single-Candidate Optimization

Sometimes only one legal action remains.

Example:

    A = CLICK Submit

In this case there is no meaningful decision for the language model to make.

The controller selects the action deterministically.

Logs distinguish:

    openjev_chat_pmi

from:

    single_candidate_autoselect

This prevents deterministic actions from being incorrectly counted as model decisions.

---

## 11. Generative Baseline

The same Gemma 3 4B model was also tested using normal autoregressive generation.

Three important observations were made:

1. A JSON-output baseline produced valid output but failed one semantic navigation workflow.
2. A weak single-letter baseline also failed that workflow.
3. A goal-focused single-letter baseline successfully completed the workflow.

Therefore the experiment does not support the claim:

    OpenJEV works while normal generation cannot.

The meaningful comparison is instead around:

- bounded action guarantees
- invalid-action risk
- semantic action quality
- option-order sensitivity
- latency
- recovery
- robustness

---

## 12. Standardized Evaluation

BrowserGym and MiniWoB++ were used for standardized browser evaluation.

The current representative Core-9 suite covers:

- click-button
- click-link
- enter-text
- choose-list
- click-checkboxes
- click-option
- click-menu
- click-dialog
- navigate-tree

The first broad evaluation produced:

    46 / 90 successful episodes
    51.11 percent

Strong task families included:

    click-button
    enter-text
    choose-list

Current weaknesses include:

    menus
    dialogs
    checkbox state management
    hierarchical navigation

These failures are preserved intentionally.

---

## 13. Current Scope

This repository demonstrates a research POC.

It is not a production browser automation platform.

The current system proves that local open-weight bounded browser control is feasible while also exposing the remaining engineering limitations.
