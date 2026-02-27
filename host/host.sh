#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$(command -v python3)" "$DIR/host.py" "$@"
