# 🎨 ThemeSwitch

Планировщик светлой/тёмной темы Windows 10/11. По расписанию переключает
режим в реестре и рассылает `WM_SETTINGCHANGE` — тема применяется
мгновенно во всех приложениях.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078d4?logo=windows)
![License](https://img.shields.io/badge/License-MIT-green)
![Dependencies](https://img.shields.io/badge/Dependencies-zero-brightgreen)

---

## ✨ Что делает

- ⏰ Несколько **сценариев** с временем начала/конца и режимом (light/dark)
- 📌 **Фиксированный режим** — `light` или `dark` всегда, выше сценариев
- 🌅 Окна через полночь работают автоматически (19:00 → 08:00)
- 📡 После записи в реестр бродкастит `WM_SETTINGCHANGE` через `user32`
- 💾 Настройки в `config.json` (создаётся при первом «Сохранить»)
- 🪶 **Без зависимостей** — только стандартная библиотека Python
- 📜 Ротация логов: 3 файла × 500 КБ (`themeswitch.log.1..3`)

---

## 🚀 Запуск

```powershell
git clone https://github.com/<your-username>/ThemeSwitch.git
cd ThemeSwitch
python main.py
```

> Только Windows 10/11. `requirements.txt` пустой — никакого `pip install`.
> Для запуска без консоли: `pythonw.exe main.py`.

При первом запуске откроется окно с двумя сценариями по умолчанию:
`08:00 → 19:00 → light` и `19:00 → 08:00 → dark`. Внизу справа —
переключатель **«Фиксировать»**: `(авто)/light/dark`.

---

## 🎛 Режимы работы

**Авто по сценариям** (по умолчанию) — планировщик раз в 30 сек
проверяет сценарии и применяет режим первого попавшего в окно.

**Фиксировано light / dark** — игнорирует все сценарии, всегда держит
выбранный режим. Удобно для презентаций, видеозвонков, работы в
одном режиме весь день. В statusbar отображается `FORCED → light`.

---

## 🖱 Как это работает

Когда планировщик тикает:

1. Если `force_mode` задан — сразу применяет его (выше сценариев).
2. Иначе — берёт первый активный сценарий (порядок = порядок в списке).
3. `theme.py` запускает `theme.ps1`.
4. PowerShell пишет в `HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize`
   (`SystemUsesLightTheme` + `AppsUseLightTheme`).
5. `user32!SendMessageTimeout` бродкастит `WM_SETTINGCHANGE` —
   все приложения перерисовываются мгновенно.

Тема — **настоящая**, не оверлей.

---

## 📁 Структура

```
ThemeSwitch/
├── main.py              # Точка входа
├── app.py               # Tkinter GUI (Treeview, force combobox)
├── theme.py             # Обёртка subprocess → PowerShell
├── theme.ps1            # Запись в реестр + broadcast WM_SETTINGCHANGE
├── scheduler.py         # Фоновый поток-планировщик (snapshot под RLock)
├── config.py            # JSON-конфиг + Scenario dataclass + RLock
├── logger.py            # RotatingFileHandler + StreamHandler
├── config.json          # Создаётся при первом «Сохранить»
├── requirements.txt     # Пустой (только stdlib)
├── LICENSE              # MIT
└── README.md
```

## 🎛 Настройки `config.json`

```json
{
  "scenarios": [
    {
      "start_hour": 8, "start_minute": 0,
      "end_hour": 19, "end_minute": 0,
      "mode": "light",
      "enabled": true
    },
    {
      "start_hour": 19, "start_minute": 0,
      "end_hour": 8, "end_minute": 0,
      "mode": "dark",
      "enabled": true
    }
  ],
  "auto_start": true,
  "force_mode": null
}
```

| Поле | Тип | Что значит |
|---|---|---|
| `scenarios[].start_hour` / `start_minute` | 0..23 / 0..59 | Когда переключить |
| `scenarios[].end_hour` / `end_minute` | 0..23 / 0..59 | Когда переключить обратно |
| `scenarios[].mode` | `light` / `dark` | Целевой режим |
| `scenarios[].enabled` | bool | Сценарий активен |
| `auto_start` | bool | Запускать планировщик сразу при старте |
| `force_mode` | `light` / `dark` / `null` | Фиксированный режим (выше сценариев) |

---

## 🪟 Сборка в .exe

```powershell
pip install pyinstaller
pyinstaller --onefile --noconsole --name ThemeSwitch main.py
```

---

## 🐛 Известные ограничения

- Только Windows 10/11 (использует системный реестр + `user32`).
- Не меняет обои и контрастные темы оформления (Accent) — только Light/Dark.
- При включённом `force_mode` ручное переключение Windows будет
  перезаписано при следующем тике планировщика (30 сек).
- При включённом автопланировщике и активном сценарии ручное
  переключение тоже будет перезаписано.

## 📝 Лицензия

MIT — делай что хочешь, только копирайт сохрани.