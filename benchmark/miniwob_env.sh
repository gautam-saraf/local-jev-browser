#!/usr/bin/env bash

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"

if [ -z "$PROJECT_ROOT" ]; then
    echo "ERROR: Could not determine repository root."
    return 1 2>/dev/null || exit 1
fi

export MINIWOB_URL="file://${PROJECT_ROOT}/third_party/miniwob-plusplus/miniwob/html/miniwob/"
