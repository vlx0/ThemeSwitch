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
- 🌅 Окна через полночь работают автоматически (19:00 → 08:00)
- 📡 После записи в реестр бродкастит `WM_SETTINGCHANGE` через `user32`
- 💾 Настройки в `config.json`
- 🪶 **Без зависимостей** — только стандартная библиотека Python

---

## 🚀 Запуск

```powershell
git clone https://github.com/<your-username>/ThemeSwitch.git
cd ThemeSwitch
python main.py
```

> Только Windows 10/11. `requirements.txt` пустой — никакого `pip install`.

При первом запуске откроется окно с двумя сценариями по умолчанию:
`08:00 → 19:00 → light` и `19:00 → 08:00 → dark`. Галочка
**«Автопланировщик»** запускает фоновый поток.

---

## 🖱 Как это работает

Когда по сценарию приходит время:

1. Планировщик определяет активный сценарий (берётся **первый**
   активный в порядке списка)
2. `theme.py` запускает `theme.ps1`
3. PowerShell пишет в `HKCU\...\Themes\Personalize`
   (`SystemUsesLightTheme` + `AppsUseLightTheme`)
4. `user32!SendMessageTimeout` бродкастит `WM_SETTINGCHANGE` —
   все приложения перерисовываются мгновенно

Тема — **настоящая**, не оверлей.

---

## 📁 Структура

```
ThemeSwitch/
├── main.py              # Точка входа
├── app.py               # Tkinter GUI
├── theme.py             # Обёртка subprocess → PowerShell
├── theme.ps1            # Запись в реестр + broadcast WM_SETTINGCHANGE
├── scheduler.py         # Фоновый поток-планировщик
├── config.py            # JSON-конфиг + Scenario dataclass
├── logger.py            # Логи в themeswitch.log
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
      "start_hour": 21, "start_minute": 0,
      "end_hour": 7,    "end_minute": 0,
      "mode": "dark",
      "enabled": true
    }
  ],
  "auto_start": true
}
```

| Поле | Тип | Что значит |
|---|---|---|
| `start_hour` / `start_minute` | 0..23 / 0..59 | Когда переключить |
| `end_hour` / `end_minute` | 0..23 / 0..59 | Когда переключить обратно |
| `mode` | `light` / `dark` | Целевой режим |
| `enabled` | bool | Сценарий активен |
| `auto_start` | bool | Запускать планировщик сразу |

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
- Если вы меняете тему вручную в настройках Windows, ThemeSwitch при
  следующем тике планировщика перезапишет ваше изменение, если есть
  активный сценарий.

## 📝 Лицензия

MIT — делай что хочешь, только копирайт сохрани.