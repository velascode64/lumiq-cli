from __future__ import annotations

import sys


def main() -> None:
    if len(sys.argv) == 1:
        from .tui import run

        run()
        return

    from .cli import main as cli_main

    cli_main()