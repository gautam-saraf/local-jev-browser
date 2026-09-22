# Third-Party Components

This project depends on several external open-source components and one external model.

Large upstream repositories and model weights are intentionally not copied into this Git repository.

This keeps the repository small, preserves clear provenance, and avoids redistributing third-party model weights.

---

## 1. OpenJEV

Upstream repository:

    https://github.com/daseinlabs/open-jev

Purpose in this project:

- local bounded option scoring
- Gemma-based decision ranking
- local /score HTTP endpoint

The exact revision used by this experiment is recorded in:

    OPENJEV_COMMIT.txt

The repository should be cloned locally under:

    third_party/open-jev

Example:

    git clone https://github.com/daseinlabs/open-jev.git third_party/open-jev
    cd third_party/open-jev
    git checkout $(cat ../../OPENJEV_COMMIT.txt)

OpenJEV source code is NOT copied into this repository.

---

## 2. Gemma 3 4B

Model used:

    google/gemma-3-4b-it

Purpose:

- local language-model inference
- bounded candidate-action scoring
- generative baseline experiments

The model weights are intentionally NOT stored in Git.

Users must obtain the model from the upstream provider and comply with the applicable access and license requirements.

Expected local location:

    third_party/open-jev/models/gemma-3-4b-it

Example download command after Hugging Face authentication:

    third_party/open-jev/.venv/bin/hf download google/gemma-3-4b-it --local-dir third_party/open-jev/models/gemma-3-4b-it

---

## 3. MiniWoB++

Upstream repository:

    https://github.com/Farama-Foundation/miniwob-plusplus

Purpose:

- standardized browser-interaction task pages
- external benchmark environment used through BrowserGym

The exact revision used in this experiment is stored in:

    MINIWOB_COMMIT.txt

Pinned revision:

    7fd85d71a4b60325c6585396ec4f48377d049838

Expected local location:

    third_party/miniwob-plusplus

Example:

    git clone https://github.com/Farama-Foundation/miniwob-plusplus.git third_party/miniwob-plusplus
    cd third_party/miniwob-plusplus
    git checkout $(cat ../../MINIWOB_COMMIT.txt)

MiniWoB++ source code is NOT copied into this repository.

---

## 4. BrowserGym

BrowserGym provides the standardized browser-agent interface used for MiniWoB evaluation.

Observed versions used in the original experiment:

    browsergym-core==0.14.3
    browsergym-miniwob==0.14.3
    gymnasium==1.3.0

Purpose:

- browser observation
- accessibility-tree state
- standardized action execution
- benchmark rewards
- termination information

Example actions include:

    click("15")
    fill("14", "Ashlea")
    select_option("13", "Croatia")

---

## 5. Playwright

Observed version:

    playwright==1.44.0

Purpose:

- local browser automation
- real-site demonstrations
- BrowserGym browser execution dependency

The project used both:

- installed Google Chrome for direct Playwright demos
- Playwright Chromium for benchmark execution

---

## 6. MLX and MLX-LM

MLX / MLX-LM are used for local inference on Apple Silicon.

Observed application version:

    mlx-lm==0.31.3

The original experiment ran on:

    Apple M2 Pro
    32 GB unified memory
    macOS

---

## 7. Why third_party/ Is Ignored

The repository contains:

    third_party/

in .gitignore.

This is intentional.

The folder can contain:

- OpenJEV source
- MiniWoB++ source
- Python environments
- Gemma model weights
- large dependency files

These should not be committed to this project repository.

Instead, the project stores:

- exact upstream repository URLs
- pinned commit IDs
- dependency versions
- setup instructions

This provides reproducibility without duplicating upstream source or model files.

---

## 8. Repository Responsibility Boundary

This repository owns:

- browser-agent integration code
- candidate-action generation logic
- experimental variants
- benchmark runners
- result summaries
- reproducibility documentation

External projects own:

- OpenJEV implementation
- MiniWoB++ task pages
- BrowserGym framework
- Playwright
- Gemma model weights

---

## 9. Recommended Reproduction Flow

A new user should:

    1. clone this repository
    2. read START_HERE.md
    3. follow QUICKSTART.md
    4. clone OpenJEV
    5. checkout OPENJEV_COMMIT.txt
    6. download Gemma 3 4B
    7. clone MiniWoB++
    8. checkout MINIWOB_COMMIT.txt
    9. create local environments
    10. start OpenJEV
    11. run the browser demo or benchmark

This separation is intentional and is part of the reproducibility design.
