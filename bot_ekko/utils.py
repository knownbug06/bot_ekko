import pygame
import importlib
import sys
from typing import Any, Type

from bot_ekko.core.logger import get_logger

logger = get_logger("Utils")


def release_pygame_display():
    pygame.display.quit()     # release framebuffer / window
    pygame.quit()             # fully release SDL video


def load_class_from_path(module_path: str, class_name: str) -> Type[Any]:
    """
    Dynamically loads a class from a given module path.
    
    Args:
        module_path (str): The dot-separated path to the module (e.g. 'bot_ekko.ui_expressions_lib.eyes.adapter')
        class_name (str): The name of the class to load (e.g. 'EyesExpressionAdapter')
        
    Returns:
        Type[Any]: The loaded class
        
    Raises:
        ImportError: If module cannot be loaded
        AttributeError: If class is not found in module
    """
    try:
        logger.info(f"Attempting to load {class_name} from {module_path}")
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls
    except ImportError as e:
        logger.error(f"Failed to import module {module_path}: {e}")
        raise
    except AttributeError as e:
        logger.error(f"Class {class_name} not found in module {module_path}: {e}")
        raise
