"""
main.py
=======
Точка входа. Запускает GUI из app.py.

Использование:
    python main.py
"""

import sys

from logger import setup as log_setup


def main() -> int:
    log_setup()  # обязательно до первого лога
    from app import App
    App().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())