"""theme.py — Python-обёртка для theme.ps1.

Два публичных API:
    get_mode()      -> "light" | "dark"
    set_mode(mode)  -> bool   (mode: "light"/"dark")

Ошибки логируются, возвращают None/False без падений.
"""

import os
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PS = _HERE / "theme.ps1"
_PWSH = "powershell"

# Кодировка для вывода PS — важно для stdout
_ENCODING = "utf-8"


def _run_ps(args, timeout=10):
    """Запустить theme.ps1 с аргументами, вернуть stdout или None."""
    if not _PS.exists():
        return None
    cmd = [_PWSH, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(_PS)] + args
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding=_ENCODING,
            errors="ignore",
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if r.returncode != 0:
            print(f"[theme] ps exit={r.returncode}: {r.stderr.strip()}", file=sys.stderr)
            return None
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        print("[theme] ps timeout", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("[theme] powershell not found", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[theme] error: {e}", file=sys.stderr)
        return None


def get_mode():
    """Return 'light' / 'dark', or None on miss."""
    out = _run_ps(["-Action", "get"])
    if out in ("light", "dark"):
        return out
    return None


def set_mode(mode):
    """Set theme: mode = 'light' or 'dark'. Return True on OK."""
    if mode not in ("light", "dark"):
        print(f"[theme] bad mode: {mode}", file=sys.stderr)
        return False
    out = _run_ps(["-Action", "set", "-Mode", mode])
    return out is not None and out.startswith("OK:")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        m = get_mode()
        print(m if m else "unknown")
    elif sys.argv[1] == "set" and len(sys.argv) >= 3:
        ok = set_mode(sys.argv[2])
        print("ok" if ok else "fail")
    elif sys.argv[1] == "get":
        m = get_mode()
        print(m if m else "unknown")