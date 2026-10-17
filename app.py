"""
app.py
======
Tkinter GUI для ThemeSwitch.

Окно:
    * Текущий режим (Light / Dark), обновляется сразу при переключении
    * Список сценариев: «08:00 → 19:00 — light», чекбокс enabled
    * Кнопки: Add, Remove, Save, Apply now
    * Автозапуск (планировщик)
    * Quit

Сворачивается в трей (pystray).
"""

import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from config import Config, Scenario, config_path
from logger import setup as log_setup
from scheduler import Scheduler
from theme import get_mode, set_mode as theme_set_mode


log = log_setup()


# ---------- ThemeController: мост между scheduler и реальной системой ----------
class ThemeController:
    """
    Адаптер: scheduler зовёт apply(mode)/disable(),
    мы переключаем тему через theme.py.
    """

    def __init__(self, on_change=None):
        self._last = None
        self._on_change = on_change  # callback(mode_or_none)

    def apply(self, mode: str) -> bool:
        if mode not in ("light", "dark"):
            return False
        ok = theme_set_mode(mode)
        if ok:
            self._last = mode
            if self._on_change:
                self._on_change(mode)
        return ok

    def disable(self) -> bool:
        # Без сценария — оставляем как есть.
        self._last = None
        if self._on_change:
            self._on_change(None)
        return True

    def last_applied(self) -> str | None:
        return self._last


# ---------- Главное окно ----------
class ThemeApp:
    REFRESH_INTERVAL_MS = 30_000  # как у scheduler

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ThemeSwitch")
        self.root.geometry("520x440")
        self.root.minsize(480, 380)

        # Иконка окна (если получится)
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self.config = Config.load(config_path())
        self.controller = ThemeController(on_change=self._on_theme_changed)
        self.scheduler = Scheduler(
            config=self.config,
            filter_=self.controller,
            on_state_change=self._on_sched_state,
        )

        self._build_ui()
        self._refresh_current_mode()

        # Запустить планировщик (если включен)
        if self.config.auto_start:
            self.scheduler.start()

        # Обновлять текущий режим раз в минуту
        self.root.after(self.REFRESH_INTERVAL_MS, self._tick_refresh)

        # Закрытие окна → сворачиваем в трей (если есть)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # --- top: текущий режим ---
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Текущий режим:", font=("", 10)).pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="—")
        self.mode_lbl = ttk.Label(top, textvariable=self.mode_var, font=("", 12, "bold"))
        self.mode_lbl.pack(side=tk.LEFT, padx=(6, 0))

        ttk.Button(top, text="Переключить сейчас", command=self._toggle_now).pack(
            side=tk.RIGHT
        )

        # --- middle: список сценариев ---
        mid = ttk.LabelFrame(self.root, text="Сценарии (время → режим)", padding=8)
        mid.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))

        cols = ("start", "end", "mode", "enabled")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=6)
        self.tree.heading("start", text="Начало")
        self.tree.heading("end", text="Конец")
        self.tree.heading("mode", text="Режим")
        self.tree.heading("enabled", text="Вкл")
        self.tree.column("start", width=110, anchor="center")
        self.tree.column("end", width=110, anchor="center")
        self.tree.column("mode", width=100, anchor="center")
        self.tree.column("enabled", width=60, anchor="center")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(mid, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.LEFT, fill=tk.Y)

        # редактирование по двойному клику
        self.tree.bind("<Double-1>", self._on_edit_cell)

        # --- middle right: кнопки ---
        btns = ttk.Frame(self.root, padding=(8, 0))
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="+ Добавить", command=self._on_add).pack(side=tk.LEFT)
        ttk.Button(btns, text="− Удалить", command=self._on_remove).pack(
            side=tk.LEFT, padx=(4, 0)
        )

        # --- bottom: автозапуск ---
        bot = ttk.Frame(self.root, padding=8)
        bot.pack(fill=tk.X)

        self.auto_var = tk.BooleanVar(value=self.config.auto_start)
        ttk.Checkbutton(
            bot,
            text="Автопланировщик (применять по сценариям)",
            variable=self.auto_var,
            command=self._on_toggle_auto,
        ).pack(side=tk.LEFT)

        ttk.Button(bot, text="Сохранить", command=self._save).pack(side=tk.RIGHT)
        ttk.Button(bot, text="Выход", command=self.quit_app).pack(side=tk.RIGHT, padx=(0, 4))

        self.status_var = tk.StringVar(value="OK")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(
            fill=tk.X, side=tk.BOTTOM
        )

        self._reload_tree()

    # ------------------------------------------------------------------ logic
    def _reload_tree(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for idx, s in enumerate(self.config.scenarios):
            self.tree.insert(
                "", "end", iid=str(idx),
                values=(s.start_str(), s.end_str(), s.mode, "✓" if s.enabled else "—"),
            )

    def _refresh_current_mode(self):
        # Не блокируем UI: get_mode() дёргает PowerShell синхронно,
        # поэтому запускаем его в фоне, а UI обновляем через after().
        def worker():
            try:
                m = get_mode()
            except Exception as e:
                log.exception("get_mode failed")
                m = None
            self.root.after(0, lambda: self._apply_refreshed_mode(m))
        threading.Thread(target=worker, daemon=True).start()

    def _apply_refreshed_mode(self, m):
        if m:
            self.mode_var.set(m)
            self.status_var.set(f"Текущий режим: {m}")
        else:
            self.mode_var.set("?")
            self.status_var.set("Не удалось прочитать режим темы")

    def _on_theme_changed(self, mode_or_none):
        if mode_or_none is None:
            self.status_var.set("Сценарий не активен — режим не меняется")
            return
        self.root.after(0, lambda: self.mode_var.set(mode_or_none))
        self.root.after(0, lambda: self.status_var.set(f"Применено: {mode_or_none}"))

    def _on_sched_state(self, in_window, mode, label):
        if not in_window:
            self.root.after(0, lambda: self.status_var.set("Нет активного сценария"))
            return
        self.root.after(0, lambda: self.status_var.set(f"Активен: {label} → {mode}"))

    def _on_toggle_auto(self):
        self.config.auto_start = self.auto_var.get()
        if self.config.auto_start:
            self.scheduler.start()
        else:
            self.scheduler.stop()
        self._save()

    def _toggle_now(self):
        # Синхронный get_mode() — это исключение из правила не блокировать UI,
        # но кнопка редкая, а без текущего режима мы не знаем что включить.
        try:
            cur = get_mode() or "dark"
        except Exception:
            cur = "dark"
        new = "dark" if cur == "light" else "light"
        ok = theme_set_mode(new)
        if ok:
            self.mode_var.set(new)
            self.status_var.set(f"Переключено на {new}")
            # Обновим _last, чтобы планировщик зря не дёргал тот же режим
            self.controller._last = new
        else:
            messagebox.showerror("Ошибка", f"Не удалось переключить тему на {new}")

    def _on_add(self):
        s = self.config.add_scenario()
        self._reload_tree()
        self._save()
        # сразу редактируем добавленную строку
        iid = str(len(self.config.scenarios) - 1)
        self.tree.selection_set(iid)
        self.tree.focus(iid)
        self._edit_scenario(iid)

    def _on_remove(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        self.config.remove_scenario(idx)
        self._reload_tree()
        self._save()

    def _on_edit_cell(self, _event):
        sel = self.tree.selection()
        if sel:
            self._edit_scenario(sel[0])

    def _edit_scenario(self, iid: str):
        idx = int(iid)
        s = self.config.scenarios[idx]

        win = tk.Toplevel(self.root)
        win.title(f"Сценарий #{idx + 1}")
        win.geometry("300x280")
        win.transient(self.root)
        win.grab_set()

        # время начала
        ttk.Label(win, text="Начало:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        sh = tk.IntVar(value=s.start_hour)
        sm = tk.IntVar(value=s.start_minute)
        ttk.Spinbox(win, from_=0, to=23, textvariable=sh, width=3).grid(row=0, column=1)
        ttk.Label(win, text=":").grid(row=0, column=2)
        ttk.Spinbox(win, from_=0, to=59, textvariable=sm, width=3).grid(row=0, column=3)

        ttk.Label(win, text="Конец:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        eh = tk.IntVar(value=s.end_hour)
        em = tk.IntVar(value=s.end_minute)
        ttk.Spinbox(win, from_=0, to=23, textvariable=eh, width=3).grid(row=1, column=1)
        ttk.Label(win, text=":").grid(row=1, column=2)
        ttk.Spinbox(win, from_=0, to=59, textvariable=em, width=3).grid(row=1, column=3)

        ttk.Label(win, text="Режим:").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        mode_var = tk.StringVar(value=s.mode)
        ttk.Combobox(win, textvariable=mode_var, values=("light", "dark"),
                     state="readonly", width=10).grid(row=2, column=1, columnspan=3, sticky="w")

        en_var = tk.BooleanVar(value=s.enabled)
        ttk.Checkbutton(win, text="Активен", variable=en_var).grid(
            row=3, column=0, columnspan=4, sticky="w", padx=8
        )

        def save_and_close():
            s.start_hour = sh.get()
            s.start_minute = sm.get()
            s.end_hour = eh.get()
            s.end_minute = em.get()
            s.mode = mode_var.get()
            s.enabled = en_var.get()
            s.__post_init__()
            self._reload_tree()
            self._save()
            win.destroy()

        ttk.Button(win, text="OK", command=save_and_close).grid(
            row=4, column=0, columnspan=4, pady=8
        )

    def _save(self):
        try:
            self.config.save(config_path())
        except OSError as e:
            log.error("save failed: %s", e)
            self.status_var.set(f"ОШИБКА сохранения: {e}")
            return
        self.scheduler.update_config(self.config)
        self.status_var.set(f"Сохранено: {len(self.config.scenarios)} сценариев")

    def _tick_refresh(self):
        self._refresh_current_mode()
        self.root.after(self.REFRESH_INTERVAL_MS, self._tick_refresh)

    # ------------------------------------------------------------------ lifecycle
    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self._refresh_current_mode()

    def _on_close(self):
        # Без трея (pystray/Pillow не включены в зависимости) — закрытие окна = выход.
        self.quit_app()

    def quit_app(self):
        try:
            self.scheduler.stop()
        except Exception:
            pass
        try:
            self.config.save(config_path())
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()