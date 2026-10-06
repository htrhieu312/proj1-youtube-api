#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$PROJECT_DIR" || exit 1

"$PROJECT_DIR/.venv/bin/python" -m elt.pipeline