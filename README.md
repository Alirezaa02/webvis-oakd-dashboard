# uavlcd

Minimal, Pi‑first Python app that drives the Enviro+ ST7735 LCD and cycles through sensor pages.  
Small modules, single entrypoint, easy to run on boot.

## Project layout

```

uavlcd/
├─ README.md
├─ requirements.txt
├─ .gitignore
├─ src/
│  └─ uavlcd/
│     ├─ __init__.py
│     ├─ main.py          # Entrypoint: config + start the app loop
│     ├─ app.py           # While-true loop, mode switching, timing
│     ├─ display.py       # ST7735 LCD wrapper (init + show)
│     ├─ sensors.py       # BME280 / LTR559 / Enviro+ gas + CPU temp
│     ├─ renderer.py      # Draw logic for graph + header text
│     ├─ modes.py         # Variable list, units, thresholds, constants
│     └─ logging_conf.py  # Logging format/level setup
├─ system/
│  └─ uavlcd.service
└─ scripts/
└─ install_service.sh  # Helper to copy/enable the systemd service

````

### What each module does

- `main.py` — tiny entrypoint; sets up logging then runs `App`.
- `app.py` — holds the main loop:
  - reads proximity to page through modes,
  - samples the active sensor,
  - maintains a per‑mode history buffer,
  - calls `renderer` to draw, then pushes to the LCD.
- `display.py` — one small class around the ST7735 driver (width/height/show).
- `sensors.py` — very thin wrappers over BME280, LTR559, and Enviro+ gas.
- `renderer.py` — converts the rolling history into a coloured bar/line plot and renders the header text (value + unit).
- `modes.py` — the list of pages (`temperature`, `pressure`, `humidity`, `light`, `oxidised`, `reduced`, `nh3`) and constants (page debounce, proximity threshold, CPU temp compensation factor).
- `logging_conf.py` — centralised logging config so logs look the same everywhere.

## Development notes

* Keep behaviour identical to the original all‑in‑one script; this structure only splits responsibilities.
* If you add a new page, update:

  * `VARIABLES` and `UNITS` in `modes.py`,
  * the `_read_variable` selector in `app.py`.
* For quick debugging, lower the loop delay in `app.py` or add extra `logging.debug` lines.

## Requirements

### Setup
Activate your virtual environment (if using one), then run ./setup_enviroplus.sh. The script mounts all tertiary requirements, along with installing all modules in requirements.txt in the same folder. Will attempt to return a useful error if it encounters a problem.
