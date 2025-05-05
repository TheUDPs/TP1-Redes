#!/usr/bin/env bash

# Exit immediately on error
set -e

if [[ -x ".venv/bin/pytest" ]]; then
    echo "Using virtualenv pytest..."
    ./.venv/bin/pytest "$@"
else
    echo "Using global pytest..."
    pytest "$@"
fi
