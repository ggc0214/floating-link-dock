#!/usr/bin/env bash
set -euo pipefail
if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "需要 Apple Silicon Mac 和原生 arm64 Python，不能在 Windows 或 Rosetta 中构建。" >&2
  exit 2
fi
cd "$(dirname "$0")/.."
exec "${PYTHON:-python3}" scripts/build_macos.py "$@"
