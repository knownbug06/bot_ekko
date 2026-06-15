# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Bot Ekko is a Raspberry Pi robot with an expressive digital face (Pygame). It runs an
event-driven state machine that reacts to sensors, gestures, Bluetooth, and time-based
schedules, then renders a corresponding facial expression. Development is possible on macOS,
but hardware-dependent features (camera, serial sensors, Bluetooth) only work on the Pi.

## Commands

```bash
# Setup (Python 3.11; uv.lock / pyproject.toml present but deps are pinned in requirements.txt)
pip install -r requirements.txt          # NOTE: picamera2 & mediapipe are Pi-only and will fail on macOS

# Run the main face/display app (entry point is main_bot.py, NOT main.py as the README says)
python main_bot.py                       # use `sudo` on the Pi for Bluetooth/Serial access

# Run the gesture-detection process (Pi only — requires picamera2 + mediapipe)
python main_gd.py

# Tests (pytest; two separate test trees)
pytest tests/                            # core / services / interrupts / media tests
pytest bot_ekko/tests/                   # renderer (eyes/bmo) + state-registry tests
pytest tests/test_interrupts.py::test_name   # run a single test
```

There is no configured linter/formatter. `tests/verify_*.py` and `tests/reproduce_*.py` are
standalone diagnostic scripts (run with `python`), not pytest cases.

## Configuration

- `bot_ekko/config.json` — the single source of runtime config (loaded as a `SystemConfig`
  pydantic model in `core/models.py`). Selects the render engine (`ui_expression_config`),
  enables/disables each service, and defines `schedules`. Changing behavior usually means
  editing this file, not code.
- `bot_ekko/sys_config.py` — compile-time constants: resolution (`LOGICAL_W/H` vs `PHYSICAL_W/H`),
  `SCREEN_ROTATION`, colors, fonts, file paths. Fonts call `pygame.font.init()` at import time.
- `.env` (see `.env_template`) — `TENOR_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`,
  loaded via `python-dotenv` in `main_bot.py`.

## Architecture

The main loop lives in `main_bot.py`. It wires together independent pieces that communicate
through a single thread-safe `queue.Queue[Command]` — services never mutate state directly.

**Data flow:** Service (sensor/gesture/BT/CLI) → `CommandCenter.issue_command()` → enqueues a
`Command` → main loop drains the queue and calls `command.execute()` → `StateHandler.set_state()`
→ render engine dispatches to the matching `handle_<STATE>` method.

Key components (`bot_ekko/core/`):

- **`state_machine.py`** — `StateMachine` holds the current state string. `StateHandler`
  (extends `BaseStateHandler`) owns transitions, a 5-deep `state_history` deque, and current
  params. It validates every target against `StateRegistry` before transitioning.
- **`state_registry.py`** — `StateRegistry` is the authoritative set of valid state names
  (ACTIVE, SLEEPING, HAPPY, CANVAS, CLOCK, etc.). `set_state` silently rejects unregistered
  states, so **new states must be added here first**.
- **`command_center.py`** — `CommandCenter` builds `Command` objects and enqueues them;
  `Command.execute()` dispatches on `CommandNames` (CHANGE_STATE / RESTORE_STATE) and handles
  `save_history`. This indirection is required: commands must carry an injected `StateHandler`.
- **`interrupts.py`** — `InterruptHandler` manages temporary, priority-based state overrides
  (e.g. a sensor proximity trigger) with durations. On the first interrupt it saves history;
  when all interrupts expire it issues RESTORE_STATE. Durations are seconds in the API but
  stored as ms internally.
- **`scheduler.py`** — time-based state changes (daily/hourly/date schedules from config).
  Driven by `BaseStateRenderer._check_schedule()` each frame; scheduler-triggered states are
  tagged with `params["_source"] = "scheduler"` so they can be reverted when the window ends.
- **`base.py`** — service lifecycle base classes: `BaseService` → `Service` (sync),
  `ThreadedService`, `ProcessService`, each with a `ServiceStatus` enum. Also defines
  `BaseStateRenderer` (the render-engine base with schedule + `handle_<STATE>` dispatch) and
  `BasePhysicsEngine`.

### Render engines (pluggable)

The render engine is **dynamically loaded by class path** in `main_bot.py` via
`load_class_from_path(adapter_module, adapter_class)` from `config.json`. It must implement
`AbstractRenderEngine` (`core/render_engine.py`): `render`, `update`, `get_physics_state`,
`set_physics_state`, `set_dependencies`. Dependencies (state_handler, command_center,
system_config) are injected *after* construction via `set_dependencies()`.

Two implementations under `bot_ekko/ui_expressions_lib/`, each with its own `adapter.py`
(extends `BaseStateRenderer`), `physics.py`, and `expressions.py`:
- **`eyes/`** — default dynamic-eye face (`MainAdapter`). **Config-driven**: every expression
  is declared as data in `eyes/expressions.json` (per-eye geometry + eyelid slants + behaviour),
  parsed into `ExpressionSpec`/`EyeSpec` by `eyes/spec.py`. `eyes/physics.py` (`EyeRig`) morphs
  the current geometry toward the target expression each frame (smooth transitions for free), and
  `eyes/expressions.py` (`EyesRenderer`) draws *any* expression generically. The adapter
  auto-registers each expression name into `StateRegistry` at startup.
- **`bmo/`** — alternative BMO-style face.

To add an eyes expression: add an entry to `eyes/expressions.json` (no code). Emotion comes from
the four `lid_*` eyelid fractions — top-inner-low = angry, top-outer-low = sad, bottom-raised =
happy, both-top-low = sleepy. Optionally add the name to `StateRegistry` for code references.
Only the media/text states (CANVAS/CHAT/CLOCK) still use `handle_<STATE>` methods.

### Services (`bot_ekko/services/`)

`MainBotServicesManager` (`core/mainbot.py`) constructs all services, filters to the
`enabled` ones from config, starts them, and calls `service_loop_update()` each frame.

- `service_sensors.py` — ESP32 over serial (`pyserial`); proximity/IMU triggers → interrupts.
- `service_bt.py` — BLE peripheral; receive commands like `STATE;HAPPY` from a phone.
- `service_gesture.py` — receives gesture JSON over Unix socket `/tmp/ekko_ipc.sock`;
  maps gestures→states via `gesture_state_mapping` in config.
- `service_cli.py` — Unix socket `/tmp/ekko_cli.sock`; controlled by the `bot_ekko/cli.py`
  client (`set_state <STATE>`).
- `service_mic.py`, `service_system_logs.py` — audio capture and CPU/GPU stats.

### Vision (separate process)

`bot_ekko/vision/gesture_detection/` runs as its **own process** (`main_gd.py`), using
MediaPipe + PiCamera2 to detect hand gestures, then pushes them to the main app over the
Unix socket via `ipc_client.send_gesture()`. The model file is `gesture_recognizer.task` at
the repo root. This decoupling keeps heavy CV work out of the render loop.

## Deployment (Raspberry Pi)

Runs as systemd units in `system_services/` (deployed to `/home/ekko/mainbot/bot_ekko`,
user `ekko`, `DISPLAY=:0`):
- `ekko_bot.service` → `main_bot.py` (the face app)
- `ekko_gd.service` → `main_gd.py` (gesture detection)
- `ekko_htspt.service` → `boot_scripts/ekko_wifi_setup.sh`, which launches a `wifi-connect`
  captive portal ("Ekko-WiFi-Setup") when no internet is detected on boot.

## Conventions

- Use `from bot_ekko.core.logger import get_logger` for logging; pass a component name.
- Never set state by mutating the `StateMachine` directly from a service — always go through
  `CommandCenter.issue_command(...)` so transitions are queued, validated, and history-tracked.
- Config is pydantic-validated; adding a config key means updating the corresponding model in
  `core/models.py`.
