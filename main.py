import time
import os
from signal import pause
from display.ssd1306 import Display
from data_handler import DataHandler

# Initialize Display
oled_display = Display()
# Data Handler
data_handler = DataHandler(display=oled_display)


if __name__ == '__main__':

    # Start the display process for device
    logo_location = os.path.join(os.getcwd(), "images", "uw-logo.png")
    oled_display.display_image(logo_location)
    time.sleep(5)
    oled_display.display_centered_text("Initializing...")

    # Initialize Data handler
    data_handler.initialize()

    # Wait indefinitely
    while True:
        if data_handler.daq_status:
            current_time = time.time()
            elapsed = current_time - data_handler.daq_start
            oled_display.display_centered_text(f"Elapsed time: {round(elapsed/60)} min")
        time.sleep(60)
