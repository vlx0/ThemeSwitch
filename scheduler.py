"""
scheduler.py
============
Фоновый поток, который раз в 30 секунд проверяет все активные сценарии
и применяет нужный режим темы.

При нескольких активных сценариях — берётся первый попавший в окно
(порядок задаёт пользователь в GUI).
"""

import threading
import time
from datetime import datetime
from typing import Callable, Optional

from config import Config, Scenario
from logger import get as get_log

log = get_log()

# Раз в сколько секунд планировщик сверяется с часами
TICK_SECONDS = 30


def _scenario_in_window(s: Scenario, now: datetime) -> bool:
    """Проверяет, попадает ли `now` в окно сценария `s`."""
    start = now.replace(
        hour=s.start_hour, minute=s.start_minute, second=0, microsecond=0
    )
    end = now.replace(
        hour=s.end_hour, minute=s.end_minute, second=0, microsecond=0
    )
    if s.crosses_midnight():
        return now >= start or now < end
    return start <= now < end


class Scheduler:
    """
    Планировщик: раз в TICK_SECONDS сверяется с активными сценариями
    и вызывает filter.apply(mode) / filter.disable().
    """

    def __init__(
        self,
        config: Config,
        filter_,
        on_state_change: Optional[Callable[[bool, str, str], None]] = None,
    ) -> None:
        """
        on_state_change(in_window, mode, label) — UI-колбэк
        при реальной смене состояния.
        """
        self._config = config
        self._filter = filter_
        self._on_state_change = on_state_change

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, name="ThemeSwitch-Scheduler", daemon=True
        )
        self._thread.start()
        log.info("Scheduler started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def update_config(self, new_config: Config) -> None:
        self._config = new_config

    # ------------------------------------------------------------------ #
    def _active_match(self, now: datetime) -> tuple[str, str] | None:
        """Возвращает (mode, label) для первого активного сценария."""
        for idx, s in enumerate(self._config.scenarios):
            if not s.enabled:
                continue
            try:
                if _scenario_in_window(s, now):
                    label = (f"#{idx + 1} "
                             f"{s.start_hour:02d}:{s.start_minute:02d}"
                             f"→"
                             f"{s.end_hour:02d}:{s.end_minute:02d}")
                    return (s.mode, label)
            except (ValueError, TypeError, AttributeError) as exc:
                log.warning("Scenario #%d skipped: %s", idx + 1, exc)
                continue
        return None

    def _loop(self) -> None:
        last_state: Optional[tuple[str, str]] = None

        while not self._stop_event.is_set():
            try:
                now = datetime.now()
                current = self._active_match(now)

                if current != last_state:
                    if current is not None:
                        mode, label = current
                        ok = self._filter.apply(mode)
                        log.info(
                            "Auto: theme=%s (scenario=%s, ok=%s)",
                            mode, label, ok,
                        )
                    else:
                        ok = self._filter.disable()
                        log.info("Auto: no active scenario, theme unchanged (ok=%s)", ok)
                    last_state = current
                    if self._on_state_change:
                        in_window = current is not None
                        mode = current[0] if current else "—"
                        label = current[1] if current else ""
                        self._on_state_change(in_window, mode, label)
            except Exception:
                log.exception("Scheduler tick failed")

            for _ in range(TICK_SECONDS):
                if self._stop_event.is_set():
                    break
                time.sleep(1)