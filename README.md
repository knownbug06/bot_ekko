# Bot Ekko

Bot Ekko is an expressive robot software stack designed to run on embedded Linux systems (like Raspberry Pi). It features procedural eye animation, emotional states, and sensor responsiveness.

## Key Features

- **Procedural Eye Rendering**: Eyes are drawn elegantly using Pygame, allowing for smooth transitions and infinite variations.
- **State Machine Architecture**: Robust state management (Active, Sleeping, Waking, Angry, etc.) ensures consistent behavior.
- **Sensor Fusion**: Reacts to external stimuli (Proximity, Distance tests) via sensor modules.
- **Media Interface**: Capable of displaying text, images, and smooth GIFs for user interaction.
- **Bluetooth Control**: (In Progress) Support for remote control via Bluetooth.

## Installation

### Prerequisites
- Python 3.7+
- Pygame
- Pillow (PIL)

### Setup
1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/bot_ekko.git
    cd bot_ekko
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: If no requirements file exists, install `pygame` and `Pillow` manually)*

## Configuration

The main configuration file is located at `bot_ekko/config.py`. Key settings include:
- `LOGICAL_W`, `LOGICAL_H`: resolution for rendering.
- `STATES`: Definitions for eye shapes and physics for each emotional state.
- `SENSOR_TRIGGER_*`: Timings for sensor engagement.

## Usage

To start the robot software, run the main entry point:

```bash
python3 main.py
```

## Architecture

- **`core/`**: contains the heart of the system.
    - `state_handler.py`: Logic for changing and maintaining states.
    - `movements.py`: Physics for eye movement.
    - `display_manager.py`: Abstraction for screen handling.
- **`modules/`**: contains feature modules.
    - `media_interface.py`: Handles non-eye visuals.
    - `sensor_fusion/`: Handles input processing.

## License

[MIT License](LICENSE)