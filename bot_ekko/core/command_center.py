from bot_ekko.core.models import CommandNames, CommandCtx
from bot_ekko.core.state_machine import StateHandler
from bot_ekko.core.logger import get_logger
import queue
from typing import Optional


logger = get_logger("CommandCenter")


class Command:
    def __init__(self, command_ctx: CommandCtx, state_handler: StateHandler):
        self.command_ctx = command_ctx
        self.state_handler = state_handler
    
    def execute(self):
        if not self.state_handler:
            logger.error("All commands must come through CommandCenter, with StateHandler injected")
            return
        # TODO: currently only supports change_state command
        if self.command_ctx.name == CommandNames.CHANGE_STATE:
            target_state = self.command_ctx.params["target_state"]
            self.state_handler.set_state(target_state, self.command_ctx.params)
        else:
            logger.warning(f"Unknown command: {self.command_ctx.name}")


class CommandCenter:
    def __init__(self, command_queue: queue.Queue, state_handler: StateHandler):
        self.command_queue = command_queue
        self.state_handler = state_handler
    
    def issue_command(self, command_name: CommandNames, *_, params: Optional[dict] = None):
        command_ctx = CommandCtx(name=command_name, params=params)
        command = Command(command_ctx, self.state_handler)
        logger.info(f"Issuing command: {command.command_ctx.name}, params: {command.command_ctx.params}") 
        self.command_queue.put(command)


