#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."
python3 test/run_tests.py
