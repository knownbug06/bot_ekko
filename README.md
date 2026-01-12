# Bot Ekko

Bot Ekko is an expressive robot software stack designed to run on embedded Linux systems (like Raspberry Pi). It features procedural eye animation, emotional states, sensor responsiveness, and LLM-powered interactions.

## Visuals

<!-- Add your Screenshots and GIFs here -->
<div align="center">
  <img src="path/to/demo.gif" alt="Bot Ekko Demo" width="600">
</div>

## Key Features

- **Procedural Eye Rendering**: Eyes are drawn elegantly using Pygame, allowing for smooth transitions and infinite variations.
- **State Machine Architecture**: Robust state management (Active, Sleeping, Waking, Angry, etc.) ensures consistent behavior.
- **Sensor Fusion**: Reacts to external stimuli (Proximity, Distance tests) via sensor modules.
- **Media Interface**: Capable of displaying text, images, and smooth GIFs for user interaction.
- **Chat API**: Integrated local server support for LLM-based chat interactions.
- **Scheduling**: Automated sleep/wake cycles managed via `schedule.json`.
- **System Health Monitoring**: Continuous logging of system stats (CPU, RAM, Temp) to `system_health.jsonl`.
- **Bluetooth Control**: (In Progress) Support for remote control via Bluetooth.

## Installation

### Prerequisites
- Python 3.11+
- Pygame
- Pillow (PIL)
- Systemd (for service management)

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/bot_ekko.git
    cd bot_ekko
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install Systemd Service (Optional):**
    To run Bot Ekko as a background service:
    ```bash
    sudo cp system_services/bot_ekko.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable bot_ekko.service
    sudo systemctl start bot_ekko.service
    ```

## Configuration

The main configuration is split between `bot_ekko/sys_config.py` (variables) and `schedule.json` (timing).

- **`bot_ekko/sys_config.py`**:
    - `LOGICAL_W`, `LOGICAL_H`: Rendering resolution.
    - `STATES`: Definitions for eye shapes and physics for each emotional state.
    - `SERVER_CONFIG`: URL and API key for the local LLM server.
    - `sytem_monitoring_enabled`: Toggle for health logging.

- **`schedule.json`**:
    - Defines `SLEEP_AT` and `WAKE_AT` times for automated power management.

## Usage

To start the robot software manually:

```bash
python3 main.py
```

## Architecture

- **`core/`**: contains the heart of the system.
    - `state_machine.py`: Manages transitions between emotional states.
    - `movements.py`: Physics for eye movement nuances.
    - `display_manager.py`: Abstraction for screen handling.
    - `scheduler.py`: Handles time-based events.
- **`modules/`**: contains feature modules.
    - `media_interface.py`: Handles non-eye visuals (images, gifs).
    - `sensor_fusion/`: Handles input processing.
    - `comms/`: Bluetooth communication logic.
- **`apis/`**:
    - `adapters/chat_api.py`: Connects to local LLM for chat.

## License

[MIT License](LICENSE)