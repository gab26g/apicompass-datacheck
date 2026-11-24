#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
# Nonsecret host configuration only. Secrets are read directly from SSM.
exec "${APICOMPASS_PYTHON:-.venv/bin/python}" scripts/runtime_secrets.py "${1:-up}"
