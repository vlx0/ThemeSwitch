"""
config.py
=========
Загрузка и сохранение пользовательских настроек ThemeSwitch в JSON.

Сценарий — «с какого времени до какого держать режим light/dark».
Может переходить через полночь (например, 21:00 → 07:00).
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict


DEFAULT_SCENARIO_DAY = (8, 0, 19, 0, "light")   # 08:00 → 19:00, light
DEFAULT_SCENARIO_NIGHT = (19, 0, 8, 0, "dark")  # 19:00 → 08:00, dark


@dataclass
class Scenario:
    """
    Один сценарий: с какого времени по какое держать указанный режим.
    Может переходить через полночь.
    """
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    mode: str   # "light" или "dark"
    enabled: bool = True

    def __post_init__(self) -> None:
        self.start_hour = max(0, min(23, int(self.start_hour)))
        self.start_minute = max(0, min(59, int(self.start_minute)))
        self.end_hour = max(0, min(23, int(self.end_hour)))
        self.end_minute = max(0, min(59, int(self.end_minute)))
        if self.mode not in ("light", "dark"):
            self.mode = "dark"
        self.enabled = bool(self.enabled)

    def crosses_midnight(self) -> bool:
        """True, если окно переходит через полночь (конец ≤ начало)."""
        return (self.end_hour, self.end_minute) <= (self.start_hour, self.start_minute)

    def start_str(self) -> str:
        return f"{self.start_hour:02d}:{self.start_minute:02d}"

    def end_str(self) -> str:
        return f"{self.end_hour:02d}:{self.end_minute:02d}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Scenario":
        known = set(cls.__dataclass_fields__.keys())
        defaults = {f: 0 for f in cls.__dataclass_fields__ if f != "mode"}
        defaults["mode"] = "dark"
        defaults["enabled"] = True
        return cls(**{**defaults, **{k: v for k, v in d.items() if k in known}})


@dataclass
class Config:
    scenarios: list[Scenario] = field(default_factory=list)
    auto_start: bool = True

    # ------------------------------------------------------------------ #
    def active_scenarios(self) -> list[Scenario]:
        return [s for s in self.scenarios if s.enabled]

    def add_scenario(self, scenario: Scenario | None = None) -> Scenario:
        if scenario is None:
            scenario = Scenario(*DEFAULT_SCENARIO_DAY, enabled=True)
        self.scenarios.append(scenario)
        return scenario

    def remove_scenario(self, index: int) -> None:
        if 0 <= index < len(self.scenarios):
            del self.scenarios[index]

    # ------------------------------------------------------------------ #
    @classmethod
    def create_default(cls) -> "Config":
        return cls(
            scenarios=[
                Scenario(*DEFAULT_SCENARIO_DAY, enabled=True),
                Scenario(*DEFAULT_SCENARIO_NIGHT, enabled=True),
            ],
            auto_start=True,
        )

    @classmethod
    def load(cls, path: Path) -> "Config":
        if not path.exists():
            return cls.create_default()
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            scenarios = [Scenario.from_dict(s) for s in raw.get("scenarios", [])]
            if not scenarios:
                return cls.create_default()
            return cls(
                scenarios=scenarios,
                auto_start=bool(raw.get("auto_start", True)),
            )
        except (json.JSONDecodeError, TypeError, ValueError, KeyError):
            return cls.create_default()

    def save(self, path: Path) -> None:
        data = {
            "scenarios": [s.to_dict() for s in self.scenarios],
            "auto_start": self.auto_start,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def config_path() -> Path:
    base = Path(os.path.dirname(os.path.abspath(__file__)))
    return base / "config.json"