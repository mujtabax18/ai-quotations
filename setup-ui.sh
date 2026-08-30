#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python 3 is required."
  exit 1
fi

if ! "$PYTHON" -c "import tkinter" >/dev/null 2>&1; then
  echo "Tkinter/Tk support is missing."
  echo
  if command -v pacman >/dev/null 2>&1; then
    echo "Install it with: sudo pacman -S tk"
  elif command -v apt >/dev/null 2>&1; then
    echo "Install it with: sudo apt install python3-tk"
  elif command -v dnf >/dev/null 2>&1; then
    echo "Install it with: sudo dnf install python3-tkinter"
  else
    echo "Install the Tk/Tkinter package for your operating system."
  fi
  exit 1
fi

if [ ! -d .venv ]; then
  "$PYTHON" -m venv .venv
fi

source .venv/bin/activate

if ! python -c "import tkinter" >/dev/null 2>&1; then
  echo "Tkinter is available system-wide but not inside this venv."
  echo "Recreate the venv after installing Tk support."
  exit 1
fi

echo
echo "Setup complete. No pip UI packages were installed."
echo "Run:"
echo "  source .venv/bin/activate"
echo "  python run_manager.py"
