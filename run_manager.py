#!/usr/bin/env python3
from __future__ import annotations

import sys


def main() -> int:
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print(
            "Tkinter is not available in this Python installation.\n\n"
            "Windows/macOS: reinstall Python with Tcl/Tk support.\n"
            "Ubuntu/Debian: sudo apt install python3-tk\n"
            "Arch/CachyOS/Manjaro: sudo pacman -S tk\n"
            "Fedora: sudo dnf install python3-tkinter\n\n"
            "After installing Tk support, reactivate the venv and run:\n"
            "  python run_manager.py\n"
        )
        return 1

    from tools.quotation_manager.app import main as run_app

    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())
