SHELL := /bin/bash

.PHONY: help verify serve demo demo-wikipedia demo-playwright miniwob

help:
	@echo ""
	@echo "Local Jev-Style Browser Control POC"
	@echo ""
	@echo "make verify            Check local dependencies"
	@echo "make serve             Start local OpenJEV server"
	@echo "make demo              Run main local browser demo"
	@echo "make demo-wikipedia    Run Wikipedia demo"
	@echo "make demo-playwright   Run Playwright docs demo"
	@echo "make miniwob           Run MiniWoB enter-text seed 42"
	@echo ""

verify:
	@test -d third_party/open-jev/.git && echo "OpenJEV source: PASS" || echo "OpenJEV source: MISSING"
	@test -x third_party/open-jev/.venv/bin/python && echo "OpenJEV environment: PASS" || echo "OpenJEV environment: MISSING"
	@test -d third_party/open-jev/models/gemma-3-4b-it && echo "Gemma model: PASS" || echo "Gemma model: MISSING"
	@test -d third_party/miniwob-plusplus/.git && echo "MiniWoB++ source: PASS" || echo "MiniWoB++ source: MISSING"
	@test -x app/.venv/bin/python && echo "App environment: PASS" || echo "App environment: MISSING"
	@test -x benchmark/.venv/bin/python && echo "Benchmark environment: PASS" || echo "Benchmark environment: MISSING"

serve:
	cd third_party/open-jev && make serve

demo:
	cd app && .venv/bin/python browser_agent_v2.py

demo-wikipedia:
	cd app && .venv/bin/python browser_agent_v3_wikipedia.py

demo-playwright:
	cd app && .venv/bin/python browser_agent_v4_playwright.py

miniwob:
	source benchmark/miniwob_env.sh && benchmark/.venv/bin/python benchmark/miniwob_jev_agent_broad_v1.py --task browsergym/miniwob.enter-text --seed 42 --headless
