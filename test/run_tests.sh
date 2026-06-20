#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."
python3 -m pytest -vv -s -m "not slow"
