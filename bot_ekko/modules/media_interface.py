import pygame
from PIL import Image
from bot_ekko.config import LOGICAL_W, LOGICAL_H, CYAN, BLACK
from bot_ekko.core.logger import get_logger

logger = get_logger("InterfaceModule")

class InterfaceModule:
    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.content_type = None # "TEXT", "IMAGE", "GIF"
        self.value = None
        self.font = pygame.font.SysFont("Arial", 50, bold=True)
        self.image_surface = None
        
        # GIF Logic
        self.gif_frames = []
        self.gif_idx = 0
        self.gif_active = False
        self.last_frame_time = 0
        self.frame_duration = 100 # ms

    def _ensure_interface_state(self):
        if self.state_machine.get_state() != "INTERFACE":
            self.state_machine.store_context()
            self.state_machine.set_state("INTERFACE")

    def set_text(self, text):
        self._ensure_interface_state()
            
        self.content_type = "TEXT"
        self.value = text
        self.image_surface = None
        self._reset_gif()

    def set_image(self, image_path):
        self._ensure_interface_state()

        self.content_type = "IMAGE"
        self.value = image_path
        self._reset_gif()
        try:
            img = pygame.image.load(image_path)
            # Use convert() for speed
            self.image_surface = pygame.transform.scale(img, (LOGICAL_W, LOGICAL_H)).convert()
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            self.set_text(f"Error: {e}")

    def set_gif(self, gif_path):
        self._ensure_interface_state()

        if self.content_type == "GIF" and self.value == gif_path and self.gif_frames:
            # Already loaded, just ensure active
            self.gif_active = True
            return

        self.content_type = "GIF"
        self.value = gif_path
        self._reset_gif()
        
        try:
            pil_img = Image.open(gif_path)
            self.gif_frames = []
            
            # Extract duration if available
            if 'duration' in pil_img.info:
                self.frame_duration = pil_img.info['duration']
            
            # Iterate frames
            try:
                while True:
                    # Convert to RGBA forpygame
                    frame = pil_img.convert("RGBA")
                    mode = frame.mode
                    size = frame.size
                    data = frame.tobytes()
                    
                    py_img = pygame.image.fromstring(data, size, mode)
                    
                    # Scale to fit screen
                    # py_img = pygame.transform.scale(py_img, (LOGICAL_W, LOGICAL_H))
                    
                    # Optimization: Convert to display format for hardware acceleration
                    # This does NOT change how it looks, but makes drawing much faster (GPU-friendly)
                    if pygame.display.get_init():
                         py_img = py_img.convert()
                    
                    self.gif_frames.append(py_img)
                    
                    pil_img.seek(pil_img.tell() + 1)
            except EOFError:
                pass # End of frames
                
            self.gif_active = True
            logger.info(f"Loaded GIF: {gif_path} ({len(self.gif_frames)} frames)")
            
        except Exception as e:
            logger.error(f"Error loading GIF: {e}")
            self.set_text(f"Error GIF: {e}")

    def _reset_gif(self):
        self.gif_frames = []
        self.gif_idx = 0
        self.gif_active = False
        self.last_frame_time = 0

    def clear(self):
        """Clears interface and restores previous state."""
        self.content_type = None
        self.value = None
        self.image_surface = None
        self._reset_gif()
        self.state_machine.restore_context()

    def draw(self, surface):
        surface.fill(BLACK)
        if self.content_type == "TEXT" and self.value:
            # Wrap text if needed or just center simple text
            text_surf = self.font.render(str(self.value), True, CYAN)
            rect = text_surf.get_rect(center=(LOGICAL_W//2, LOGICAL_H//2))
            surface.blit(text_surf, rect)
            
        elif self.content_type == "IMAGE" and self.image_surface:
            rect = self.image_surface.get_rect(center=(LOGICAL_W//2, LOGICAL_H//2))
            surface.blit(self.image_surface, rect)
            
        elif self.content_type == "GIF" and self.gif_active and self.gif_frames:
             now = pygame.time.get_ticks()
             if now - self.last_frame_time > self.frame_duration:
                 self.gif_idx = (self.gif_idx + 1) % len(self.gif_frames)
                 self.last_frame_time = now
             
             current_frame = self.gif_frames[self.gif_idx]
             rect = current_frame.get_rect(center=(LOGICAL_W//2, LOGICAL_H//2))
             surface.blit(current_frame, rect)
