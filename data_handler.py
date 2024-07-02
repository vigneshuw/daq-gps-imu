import time
import sys
from IMU.imudevice import IMUPoller
from GPS.gpsdevice import GPSPoller
from button import ButtonHandler


class DataHandler:
    def __init__(self, daq_pin=16, transfer_pin=25):

        # TODO: Add LED

        # Initialize
        self.daq_pin = daq_pin
        self.transfer_pin = transfer_pin

        # Sensors
        self.gps_poller = None
        self.imu_poller = None

        # Buttons
        self.button_daq = None

        # Status
        self.daq_status = False

    def initialize(self):

        # Buttons
        self.button_daq = ButtonHandler(pin=16, on_button_held_callback=self.start_daq,
                                        on_button_released_callback=self.stop_daq, press_duration=2)

    def start_daq(self):

        # Maintain time
        daq_start = int(time.time())

        # GPS
        self.gps_poller = GPSPoller(save_dir_time=str(daq_start))
        self.gps_poller.start_polling()

        # IMU
        self.imu_poller = IMUPoller(save_dir_time=str(daq_start))
        self.imu_poller.start_polling()

        self.daq_status = True
        sys.stdout.write("Data collection in progress\n")

    def stop_daq(self):
        # Stop the DAQ process
        self.gps_poller.stop_polling()
        self.imu_poller.stop_polling()

        self.daq_status = False
        sys.stdout.write("Data collection stopped\n")
