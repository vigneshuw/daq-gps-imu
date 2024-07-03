import time
import os
from signal import pause
from display.ssd1306 import Display
from data_handler import DataHandler

# Initialize Display
oled_display = Display(logo_loc=os.path.join(os.getcwd(), "images", 'uw-logo.png'))
# Data Handler
data_handler = DataHandler(display=oled_display)


if __name__ == '__main__':

    # Initialize the system
    oled_display.display_centered_text("Initializing...")
    # Data handler
    data_handler.initialize()

    # Wait indefinitely
    while True:
        if data_handler.daq_status:
            current_time = time.time()
            elapsed = current_time - data_handler.daq_start
            oled_display.display_centered_text(f"Elapsed time: {round(elapsed/60)} min")
        time.sleep(60)
