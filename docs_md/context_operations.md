# Context Operations in State Machine

## Overview
**Bot Ekko** relies on a state machine to manage its behavior (e.g., `ACTIVE`, `SLEEPING`, `SQUINTING`, `CANVAS`). "Context Operations" refer to the mechanism of saving the current state (including eye position and parameters) before switching to a temporary state, and then restoring it afterwards.

This allows the robot to seamlessly handle interruptions like:
- **Sensor Triggers**: (e.g., Distance sensor triggers `SQUINTING` -> return to `ACTIVE`)
- **Media Playback**: (e.g., Play a GIF -> return to `ACTIVE`)
- **Menus/Interfaces**: (e.g., Open settings -> return to `ACTIVE`)

## The Approach: Centralized Command Control

Previously, logic for saving/restoring state was scattered across various modules. We have centralized this into the **Command Center**.

### 1. Saving Context
When you want to switch to a temporary state, you set `save_history=True` in the `CHANGE_STATE` command parameters.

**Mechanism:**
1.  `CommandCenter` receives `CHANGE_STATE` command.
2.  It checks for `save_history=True`.
3.  If True, it calls `state_handler.save_state_ctx()`, pushing the *current* state onto a history stack.
4.  Then, it applies the *new* state.

**Usage:**
```python
# Switch to 'CANVAS' state but remember where we were
params = {
    "target_state": "CANVAS",
    "save_history": True
}
command_center.issue_command(CommandNames.CHANGE_STATE, params=params)
```

### 2. Restoring Context
When a temporary state is finished (e.g., media ends, or sensor clears), we issue a `RESTORE_STATE` command.

**Mechanism:**
1.  `CommandCenter` receives `RESTORE_STATE` command.
2.  It calls `state_handler.restore_state_ctx()`.
3.  The `StateHandler` pops the last saved context from the history stack and reverts the robot to that state.

**Usage:**
```python
# Go back to whatever we were doing before
command_center.issue_command(CommandNames.RESTORE_STATE)
```

## Module Responsibilities

- **CommandCenter**: The gatekeeper. Handles the actual `save()` and `restore()` logic during command execution.
- **InterruptManager**: Automatically requests `save_history=True` when it triggers the *first* interrupt in a sequence. When all interrupts clear, it issues `RESTORE_STATE`.
- **MediaModule**: When playback finishes, it simply issues `RESTORE_STATE`. It does *not* manage saving; it assumes the caller (who started the media) requested `save_history=True` if they wanted auto-return.
- **Adapters (e.g. GifAPI)**: Responsible for requesting `save_history=True` when they trigger a playback state.

## Decision Logic: When is a State Temporary?
We do not hardcode "Temporary" vs "Permanent" properties on the states themselves. Instead, we rely on the **intent of the caller**:

1.  **Interrupts are always temporary**: The `InterruptManager` assumes that if it is interrupting the robot, it should eventually return. Therefore, it *always* sets `save_history=True` for the first interrupt.
2.  **Media is usually temporary**: Most media (GIFs, text alerts) are transient. Modules like `GifAPI` explicitly request `save_history=True`.
3.  **Mode Switches are permanent**: If the user uses a Bluetooth command to explicitly set `STATE;SLEEP`, that command generally does *not* set `save_history=True`, making it a permanent switch.

This explicit approach avoids ambiguity and gives us full control over the navigation stack.

## Benefits
- **No Circular Dependencies**: Lower-level modules don't need to know about high-level state logic.
- **Predictability**: State history is only modified explicitly via commands.
- **Robustness**: Prevents "infinite loops" where a state might be restored incorrectly if manually handled in multiple places.
