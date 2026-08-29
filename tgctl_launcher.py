from __future__ import annotations

import sys


def run() -> int:
    if "--smoke-test" in sys.argv:
        import telegram_exporter.daemon_main  # noqa: F401
        import telegram_exporter.ipc_client  # noqa: F401
        import telegram_exporter.tgctl  # noqa: F401
        return 0

    from telegram_exporter.tgctl import main

    return main()


if __name__ == "__main__":
    raise SystemExit(run())
