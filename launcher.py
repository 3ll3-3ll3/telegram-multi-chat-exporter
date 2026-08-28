from __future__ import annotations

import sys


def _smoke_test() -> int:
    # Import the packaged GUI module without opening a window. GitHub Actions
    # uses this to catch missing hidden imports / packaging regressions.
    import telegram_exporter.gui  # noqa: F401

    return 0


def run() -> int:
    if "--smoke-test" in sys.argv:
        return _smoke_test()

    from telegram_exporter.main import main

    return main()


if __name__ == "__main__":
    raise SystemExit(run())
