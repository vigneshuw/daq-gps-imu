import pickle
import time
from signal import pause
from gpsdevice import GPSPoller, GPSCommandSender
from button import ButtonHandler

# Data Collection params
daq_start_time = None
daq_end_time = None


# Configure GPS device
gpsc = GPSCommandSender(baudrate=9600)
# Update GPS DAQ params
gpsc.send_command("rate-10")
time.sleep(1)
gpsc.send_command("baud-115200")
# Initialize DAQ
gpsp = GPSPoller()


# Callbacks for data collection
def start_daq():
    gpsp.start_polling()


def stop_daq():
    gpsp.stop_polling()


# Setup buttons
button_daq = ButtonHandler(pin=16, on_button_held_callback=start_daq, on_button_released_callback=stop_daq,
                           press_duration=5)


if __name__ == '__main__':
    pause()
