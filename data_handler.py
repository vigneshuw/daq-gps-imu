import time
import logging
import os
from data_loader.usb import SensorDataCopier
from IMU.imudevice import IMUPoller
from GPS.gpsdevice import GPSPoller
from button import ButtonHandler


class DataHandler:
    def __init__(self, display, gps_fix_state, save_location="/sensor_data", daq_pin=16, transfer_pin=25):

        # Display
        self.display = display
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize
        self.daq_pin = daq_pin
        self.transfer_pin = transfer_pin

        # Sensors
        self.gps_poller = None
        self.gps_fix_state = gps_fix_state
        self.configure_gps = True
        self.imu_poller = None

        # Buttons
        self.button_daq = None
        self.button_download = None

        # Status
        self.daq_status = False
        self.copy_status = False
        self.daq_start = None

        # Data Copier
        self.save_location = save_location
        self.data_copier = SensorDataCopier(self.display, save_location)

    def initialize(self):

        # Buttons
        self.button_daq = ButtonHandler(pin=16, on_button_held_callback=self.start_daq,
                                        on_button_released_callback=self.stop_daq, press_duration=3)
        self.button_download = ButtonHandler(pin=12, on_button_held_callback=self.start_copy,
                                             on_button_released_callback=None, press_duration=3, release_required=False)
        # Display ready status
        self.display.display_system_props()

    def start_daq(self):

        # Verify if DAQ can be started
        if self.copy_status:
            self.display.display_header_and_status("DAQ", "Copying! Be Patient")
            return

        # Getting the directory to save
        dirs = os.listdir(self.save_location)
        existing_trial_counts = [int(x[6:]) for x in dirs if x[0:6] == "trial-"]
        if existing_trial_counts:
            max_trial = max(existing_trial_counts)
        else:
            max_trial = 0
        save_dir = "trial-" + str(max_trial + 1)
        self.display.display_header_and_status("DAQ", f"Starting {save_dir}")
        time.sleep(2)

        # Maintain time
        self.daq_status = True
        self.daq_start = int(time.monotonic())

        # GPS
        self.gps_poller = GPSPoller(save_dir_time=save_dir, configure_gps=self.configure_gps,
                                    gps_fix_indicator=self.gps_fix_state)
        self.configure_gps = False
        self.gps_poller.start_polling()

        # IMU
        self.imu_poller = IMUPoller(save_dir_time=save_dir)
        self.imu_poller.start_polling()

        self.logger.info("Data collection started")
        self.display.display_header_and_status("DAQ", "DAQ In progress...",  indicator=self.gps_fix_state[0])

    def stop_daq(self):

        # Check for DAQ running
        if not self.daq_status:
            return

        self.display.display_header_and_status("DAQ", "Stopping...")

        # Stop the DAQ process
        self.gps_poller.stop_polling()
        self.imu_poller.stop_polling()

        self.daq_status = False
        self.daq_start = None
        self.logger.info("Data collection stopped")
        # Display ready status
        self.display.display_system_props()

    def start_copy(self):
        if self.daq_status:
            self.display.display_header_and_status("Data Copy", "Cannot Copy. Stop DAQ")
            self.logger.warning("Tried copying when the DAQ is running.")
            return

        # Deactivate the DAQ Process
        self.button_daq.deactivate()
        self.button_download.deactivate()
        # Copy the data
        self.copy_status = True
        self.data_copier.copy_sensor_data()
        self.copy_status = False

        # Display ready status
        time.sleep(5)
        # Reactivate the DAQ Process
        self.button_daq.reactivate()
        self.button_download.reactivate()
        self.display.display_system_props()
