import os
import shutil
import time
import logging
import tarfile
import subprocess


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

        # Check for firmware update file
        fw_update_file = os.path.join(self.usb_mount_point, '__drivesense_fwupdate.tar')
        if os.path.exists(fw_update_file):
            self.fw_update()
            return

        try:
            destination_path = os.path.join(self.usb_mount_point, 'uw-sensor-data')
            os.makedirs(destination_path, exist_ok=True)

            # Check for available files
            num_files = len(os.listdir(self.sensor_data_path))
            if num_files == 0:
                self.status_display.display_header_and_status(header="Data Copy", status="No Data!")
                self.logger.info("Tried copy with no data")
                return

            self.status_display.display_header_and_status(header="Data Copy", status="Copy In Progress...")
            for index, folder_name in enumerate(os.listdir(self.sensor_data_path)):
                folder_path = os.path.join(self.sensor_data_path, folder_name)
                if os.path.isdir(folder_path):

                    # Before transferring, check for existing files in the USB
                    target_folder_path = os.path.join(destination_path, folder_name)
                    if os.path.exists(target_folder_path):
                        base_name = folder_name
                        counter = 1
                        while os.path.exists(target_folder_path):
                            target_folder_path = os.path.join(destination_path, f"{base_name}_{counter}")
                            counter += 1

                    shutil.copytree(folder_path, target_folder_path)
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

    def fw_update(self):
        # Initiating fw update
        self.logger.info("Updating Device FW")
        reboot = False
        self.status_display.display_header_and_status(header="FW Update", status="Updating Firmware...")

        # Get the files
        fw_update_file = os.path.join(self.usb_mount_point, '__drivesense_fwupdate.tar')
        extract_path = os.path.join(self.usb_mount_point, 'fw_update_extracted')
        os.makedirs(extract_path, exist_ok=True)

        try:
            # Extract files
            with tarfile.open(fw_update_file) as tar:
                tar.extractall(path=extract_path)

            # Check for drivesense and version.txt
            drivesense_executable = os.path.join(extract_path, 'drivesense')
            if os.path.exists(drivesense_executable):
                self.logger.info("Firmware files found. Updating system...")

                # Copy files to /opt/drivesense
                os.makedirs('/opt/drivesense/updater', exist_ok=True)
                shutil.copy(fw_update_file, '/opt/drivesense/updater')

                self.status_display.display_header_and_status(header="FW Update",
                                                              status="Complete! Rebooting...")
                self.logger.info("Firmware update completed successfully. Rebooting system...")
                time.sleep(5)
                reboot = True
            else:
                self.status_display.display_header_and_status(header="FW Update", status="Invalid FW Package!")
                self.logger.error("Invalid firmware package")

        except Exception as e:
            self.logger.error(f"Error during firmware update: {e}")
            self.status_display.display_header_and_status("Firmware Update", "Firmware Update Failed")

        finally:
            # Clean up
            if os.path.exists(fw_update_file):
                os.remove(fw_update_file)
            if os.path.exists(extract_path):
                shutil.rmtree(extract_path)

        if reboot:
            subprocess.run(['sudo', 'reboot'])
