import pygame
from bot_ekko.modules.media_interface import MediaModule
from bot_ekko.sys_config import *
import time

def verify_text_wrapping():
    # Initialize Pygame font (needed for font rendering)
    pygame.font.init()
    
    # Mock manager/center not needed for this specific test usually, but MediaModule init requires them
    # We can pass None/Mock if they are just stored and not used immediately in init
    # MediaModule init: self.interrupt_manager = interrupt_manager...
    
    media = MediaModule(None, None)
    
    # Test case 1: Short text (no wrap)
    short_text = "Hello World"
    # LOGICAL_W - 40 = 760
    max_width = 760
    
    surf_short = media._render_wrapped_text(short_text, MAIN_FONT, CYAN, max_width)
    print(f"Short text surface size: {surf_short.get_size()}")
    
    # Check height - should be approx line height
    line_h = MAIN_FONT.get_height()
    if surf_short.get_height() <= line_h * 1.5: # Allow some buffer
        print("PASS: Short text did not wrap.")
    else:
        print("FAIL: Short text wrapped unexpectedly.")

    # Test case 2: Long text (should wrap)
    # 760 px wide. 'A' is approx 20-30px? 
    # Let's make a very long string.
    long_text = "This is a very long text string that is definitely going to exceed the maximum width of the screen which is set to seven hundred and sixty pixels so it must wrap to multiple lines to be visible."
    
    surf_long = media._render_wrapped_text(long_text, MAIN_FONT, CYAN, max_width)
    print(f"Long text surface size: {surf_long.get_size()}")
    
    if surf_long.get_height() > line_h * 1.5:
        print("PASS: Long text wrapped to multiple lines.")
    else:
        print(f"FAIL: Long text did not wrap. Height: {surf_long.get_height()}, Line Height: {line_h}")
        
    # Test case 3: Very long word
    long_word = "A" * 100 # Might not wrap if logic doesn't split words, but logic says "append(word)" so it will be one long line extending beyond?
    # Logic: if w < max_width ... else ... lines.append(word)
    # If a single word is wider than max_width, it is added as a line. So it won't wrap *within* the word, but it will be on its own line.
    
    # Let's test calling show_text updates state correctly
    media.show_text(short_text, duration=1)
    if media.text_surface is not None:
        print("PASS: show_text updated text_surface.")
    else:
        print("FAIL: show_text did not update text_surface.")

if __name__ == "__main__":
    try:
        verify_text_wrapping()
    except Exception as e:
        print(f"An error occurred: {e}")
