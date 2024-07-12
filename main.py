import time
import logging
import os
from display.ssd1306 import Display
from data_handler import DataHandler
from datetime import datetime

# Initialize logging
log_directory = "/var/drivesense/logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)
# Create log file
log_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file = os.path.join(log_directory, log_timestamp + ".log")
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# GPS Info
gps_fix_state = [0]

# Initialize Display
script_dir = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(script_dir, 'images', 'uw-logo.png')
oled_display = Display(logo_loc=image_path)
# Data Handler
data_handler = DataHandler(display=oled_display, gps_fix_state=gps_fix_state)


# Version
def get_version():
    version_file = os.path.join(os.path.dirname(__file__), 'VERSION')
    with open(version_file, 'r') as vf:
        return vf.read().strip()


if __name__ == '__main__':

    # Log the application version
    version = get_version()
    logger.info(f'Starting application. Version - {version}')

    # Initialize the system
    oled_display.display_header_and_status("System Check", f"Initializing v{version}...")
    time.sleep(2)
    # Data handler
    data_handler.initialize()

    # Wait indefinitely
    while True:
        if data_handler.daq_status:
            current_time = time.monotonic()
            elapsed = current_time - data_handler.daq_start
            oled_display.display_header_and_status("DAQ", f"Elapsed time: {round(elapsed/60)} min", indicator=gps_fix_state[0])
        elif data_handler.copy_status:
            pass
        else:
            oled_display.display_system_props()
        time.sleep(60)
