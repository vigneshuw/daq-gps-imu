import os
import shutil
import sys
import time
import logging


class SensorDataCopier:
    def __init__(self, status_display, sensor_data_path='/sensor_data', usb_mount_point='/mnt/data'):
        self.sensor_data_path = sensor_data_path
        self.usb_mount_point = usb_mount_point

        # Status display
        self.status_display = status_display

        # Logging
        self.logger = logging.getLogger(self.__class__.__name__)

    def is_usb_mounted(self):
        return os.path.ismount(self.usb_mount_point)

    def test_progress(self):
        for i in range(100):
            self.status_display.display_progress("Data Copy", i / 100)
            time.sleep(0.5)

    def copy_sensor_data(self):
        if not self.is_usb_mounted():
            self.status_display.display_header_and_status(header="Data Copy", status="USB Not Found!")
            self.logger.warning("USB Not Found!")
            return

        try:
            destination_path = os.path.join(self.usb_mount_point, 'uw-sensor-data')
            os.makedirs(destination_path, exist_ok=True)

            # Check for available files
            num_files = len(os.listdir(self.sensor_data_path))
            if num_files == 0:
                self.status_display.display_header_and_status(header="Data Copy", status="No Data!")
                return

            self.status_display.display_header_and_status(header="Data Copy", status="Copy In Progress...")
            for index, folder_name in enumerate(os.listdir(self.sensor_data_path)):
                folder_path = os.path.join(self.sensor_data_path, folder_name)
                if os.path.isdir(folder_path):
                    shutil.copytree(folder_path, os.path.join(destination_path, folder_name))
                    shutil.rmtree(folder_path)

                # Update progress
                self.status_display.display_progress("Data Copy", index/num_files)

            self.logger.info("Data copy successful")
            self.status_display.display_header_and_status(header="Data Copy", status="Copy Successful!")

        except Exception as e:
            self.logger.error(f"Error while copying sensor data: {e}")
            if not self.is_usb_mounted():
                self.logger.error("USB Device removed during copy")
                self.status_display.display_header_and_status("Data Copy", "Copy Failed")
