import threading
import time
import pygame
from PIL import Image, ImageSequence
from bot_ekko.core.logger import get_logger
from bot_ekko.sys_config import *
# from bot_ekko.core.interrupt_manager import InterruptManager # Avoid circular import via TYPE_CHECKING
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from bot_ekko.core.interrupt_manager import InterruptManager
    from bot_ekko.core.command_center import CommandCenter

from bot_ekko.core.models import CommandNames

logger = get_logger("MediaModule")

class MediaModule(threading.Thread):
    def __init__(self, interrupt_manager, command_center):
        super().__init__(daemon=True)
        self.interrupt_manager = interrupt_manager
        self.command_center = command_center
        self.current_media_type = None
        self.media_end_time = 0
        self.current_interrupt_name = None
        
        # Internal state
        self.is_playing = False
        
        # Threading control
        self.running = True
        self.lock = threading.Lock()
        
        # GIF specific
        self.gif_frames = []
        self.gif_delays = []
        self.current_frame_index = 0
        self.last_frame_time = 0
        
        # Image specific
        self.current_image = None
        
        # Text specific
        self.current_text = ""
        self.text_surface = None
        
        # Cache
        self.gif_cache = {}

    def _start_media(self, duration=None, save_context=True, interrupt_name=None):
        """Helper to start media playback and handling state context."""
        # Note: Context saving is now handled by CommandCenter before switching state if requested.
            
        self.current_interrupt_name = interrupt_name
        self.is_playing = True
        
        if duration:
            self.media_end_time = time.time() + duration
        else:
            self.media_end_time = 0 # Indefinite or controlled by logic (like GIF loop)

    def play_gif(self, path, duration=None, save_context=True, interrupt_name=None):
        try:
            frames = []
            delays = []
            
            # Check cache
            if path in self.gif_cache:
                frames, delays = self.gif_cache[path]
            else:
                pil_image = Image.open(path)
                
                # Extract frames and duration
                for frame in ImageSequence.Iterator(pil_image):
                    # Convert to RGBA and then to pygame surface
                    frame_rgba = frame.convert("RGBA")
                    mode = frame_rgba.mode
                    size = frame_rgba.size
                    data = frame_rgba.tobytes()
                    
                    py_image = pygame.image.fromstring(data, size, mode)
                    frames.append(py_image)
                    delays.append(frame.info.get('duration', 100) / 1000.0) # Convert ms to seconds
                
                if frames:
                    self.gif_cache[path] = (frames, delays)

            if not frames:
                logger.error(f"No frames found in GIF: {path}")
                return

            with self.lock:
                self.gif_frames = frames
                self.gif_delays = delays
                self.current_frame_index = 0
                self.last_frame_time = time.time()
                self.current_media_type = "GIF"
            
            self._start_media(duration, save_context, interrupt_name)
            logger.info(f"Playing GIF: {path} for {duration}s")
            
        except Exception as e:
            logger.error(f"Failed to load GIF {path}: {e}")

    def show_image(self, path, duration=5.0, save_context=True, interrupt_name=None):
        try:
            image = pygame.image.load(path)
            with self.lock:
                self.current_image = image
                self.current_media_type = "IMAGE"
            self._start_media(duration, save_context, interrupt_name)
            logger.info(f"Showing Image: {path} for {duration}s")
        except Exception as e:
            logger.error(f"Failed to load Image {path}: {e}")

    def _render_wrapped_text(self, text, font, color, max_width):
        """Helper to render text wrapped to a max width."""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            w, h = font.size(test_line)
            if w < max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Word itself is too long, just add it (or could split char by char)
                    lines.append(word)
                    current_line = []
        
        if current_line:
            lines.append(' '.join(current_line))
            
        # Render lines
        rendered_lines = [font.render(line, True, color) for line in lines]
        
        # specific case for empty text
        if not rendered_lines:
             return font.render("", True, color)

        total_height = sum(line.get_height() for line in rendered_lines)
        max_line_width = max(line.get_width() for line in rendered_lines)
        
        # Create surface
        # We use transparent background
        surface = pygame.Surface((max_line_width, total_height), pygame.SRCALPHA)
        
        y = 0
        for line_surf in rendered_lines:
            # Center confirm? Or Left align?
            # Let's center align each line relative to the widest line for aesthetics
            x = (max_line_width - line_surf.get_width()) // 2
            surface.blit(line_surf, (x, y))
            y += line_surf.get_height()
            
        return surface

    def show_text(self, text, duration=CANVAS_DURATION, save_context=True, interrupt_name=None):
        # Render text wrapped
        # LOGICAL_W is 800, let's use 760 for padding
        text = text.capitalize()
        max_width = LOGICAL_W - 40 
        surf = self._render_wrapped_text(text, MAIN_FONT, CYAN, max_width)
        
        with self.lock:
            self.current_text = text
            self.text_surface = surf
            self.current_media_type = "TEXT"
        self._start_media(duration, save_context, interrupt_name)
        logger.info(f"Showing Text for {duration}s")

    def stop_media(self):
        """Stops media and restores state."""
        if self.is_playing:
            self.is_playing = False
            with self.lock:
                self.current_media_type = None
            
            if self.current_interrupt_name:
                logger.info(f"Clearing interrupt: {self.current_interrupt_name}")
                self.interrupt_manager.clear_interrupt(self.current_interrupt_name)
                self.current_interrupt_name = None
            else:
                logger.info("Restoring state via CommandCenter")
                self.command_center.issue_command(CommandNames.RESTORE_STATE)
            logger.info("Media stopped.")

    def run(self):
        """Background loop to handle media timing and updates."""
        logger.info("MediaModule thread started")
        while self.running:
            if not self.is_playing:
                time.sleep(0.1)
                continue

            # Check duration expiry
            if self.media_end_time > 0 and time.time() > self.media_end_time:
                self.stop_media()
                continue

            with self.lock:
                media_type = self.current_media_type
                
            if media_type == "GIF":
                now = time.time()
                with self.lock:
                    if self.gif_delays:
                        current_delay = self.gif_delays[self.current_frame_index]
                    else:
                        current_delay = 0.1
                    
                if now - self.last_frame_time >= current_delay:
                    with self.lock:
                        if self.gif_frames:
                            self.current_frame_index = (self.current_frame_index + 1) % len(self.gif_frames)
                            self.last_frame_time = now
                    # Calculate sleep to avoid busy loop, but be responsive
                    time.sleep(max(0.001, current_delay - (time.time() - now)))
                else:
                    time.sleep(0.01)
            else:
                 time.sleep(0.1)

    def update(self, surface):
        """
        Renders the current media frame to the surface.
        Safe to call from main thread.
        """
        if not self.is_playing:
            return

        with self.lock:
            media_type = self.current_media_type
            
            if media_type == "GIF":
                if self.gif_frames:
                    frame = self.gif_frames[self.current_frame_index]
                    rect = frame.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2))
                    surface.blit(frame, rect)
                
            elif media_type == "IMAGE":
                if self.current_image:
                    rect = self.current_image.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2))
                    surface.blit(self.current_image, rect)
                    
            elif media_type == "TEXT":
                if self.text_surface:
                     rect = self.text_surface.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2))
                     surface.blit(self.text_surface, rect)
