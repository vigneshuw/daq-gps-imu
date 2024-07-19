import os
import shutil
import time
import logging
import tarfile
import subprocess
import json


class SensorDataCopier:
    def __init__(self, status_display, sensor_data_path='/sensor_data', usb_mount_point='/mnt/data'):
        self.sensor_data_path = sensor_data_path
        self.usb_mount_point = usb_mount_point

        # Status display
        self.status_display = status_display

        # Logging
        self.logger = logging.getLogger(self.__class__.__name__)

    def is_usb_mounted(self):
        """
        Check if the device is mounted to the USB port

        :return: None
        """

        return os.path.ismount(self.usb_mount_point)

    def test_progress(self):
        """
        Display test code

        :return: None
        """

        for i in range(100):
            self.status_display.display_progress("Data Copy", i / 100)
            time.sleep(0.5)

    def copy_sensor_data(self):
        """
        Copy the sensor data to the usb mounted device.

        :return: None
        """

        if not self.is_usb_mounted():
            self.status_display.display_header_and_status(header="Data Copy", status="USB Not Found!")
            self.logger.warning("USB Not Found!")
            return

        # Check for firmware update file
        fw_update_file = os.path.join(self.usb_mount_point, '__drivesense_fwupdate.tar')
        if os.path.exists(fw_update_file):
            self.fw_update()
            return

        # Check for system config information
        system_config_file = os.path.join(self.usb_mount_point, '__drivesense_system_config.json')
        if os.path.exists(system_config_file):
            self.system_config(system_config_file)
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
                    os.sync()   # immediate flush data to device
                    shutil.rmtree(folder_path)

                # Update progress
                self.status_display.display_progress("Data Copy", index/num_files)

            self.logger.info("Data copy successful")
            self.status_display.display_header_and_status(header="Data Copy",
                                                          status="Copy Successful!\nDevice Unmounted")
            
            # Unmount the USB drive
            subprocess.run(["sudo", "umount", self.usb_mount_point], check=True)
            self.logger.info("USB Drive unmounted successful")

        except Exception as e:
            self.logger.error(f"Error while copying sensor data: {e}")
            if not self.is_usb_mounted():
                self.logger.error("USB Device removed during copy")
                self.status_display.display_header_and_status("Data Copy", "Copy Failed")

    def fw_update(self):

        """
        Firmware update for the DAQ software

        :return: None
        """

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

    def get_wifi_ip(self):
        try:
            ip_address = subprocess.check_output(["hostname", "-I"]).decode().split()[0]
            return ip_address
        except Exception as e:
            self.logger.error(f"Error getting WiFi IP address: {e}")
            return None

    def get_mac_address(self):
        try:
            mac_address = subprocess.check_output(["cat", "/sys/class/net/wlan0/address"]).decode().strip()
            return mac_address
        except Exception as e:
            self.logger.error(f"Error getting MAC address: {e}")
            return None

    def connect_to_wifi(self, ssid, password):
        try:
            # Connect to Wi-Fi using nmcli
            subprocess.run(['sudo', 'nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password], check=True)

            # Check if the Wi-Fi connection is successful
            ip_address = self.get_wifi_ip()
            if ip_address:
                self.logger.info(f"Connected to WiFi network {ssid} with IP address {ip_address}")
                return ip_address
            else:
                self.logger.error("Failed to connect to WiFi network")
                return None
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error connecting to WiFi network: {e}")
            return None

    def get_logs(self):
        try:
            log_source_dir = "/var/drivesense/logs"
            log_dest_dir = os.path.join(self.usb_mount_point, "uw-sensor-config", "logs")
            if not os.path.exists(log_dest_dir):
                os.makedirs(log_dest_dir)
            else:
                shutil.rmtree(log_dest_dir)

            for log_file in os.listdir(log_source_dir):
                full_log_path = os.path.join(log_source_dir, log_file)
                if os.path.isfile(full_log_path):
                    shutil.copy(full_log_path, log_dest_dir)

            self.logger.info(f"Logs copied to {log_dest_dir}")
        except Exception as e:
            self.logger.error(f"Error copying logs: {e}")

    def system_config(self, system_config_file):
        self.status_display.display_header_and_status(header="System Config", status="Applying Configuration...")
        self.logger.info("Applying system configuration")

        # Parse the file
        with open(system_config_file, 'r') as f:
            config = json.load(f)
        output_dir = os.path.join(self.usb_mount_point, "uw-sensor-config")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "__drivesense_system_config_output.json")

        try:
            output = {}
            # Get IP address
            if config["type"] == 'getIP':
                ip_address = self.get_wifi_ip()
                if ip_address:
                    output["status"] = "success"
                    output["ip"] = ip_address
                    self.status_display.display_header_and_status(header="System Config", status="IP Obtained")
                else:
                    output["status"] = "failed"
                    self.status_display.display_header_and_status(header="System Config", status="Failed")

            # Connect to Wi-Fi
            elif config["type"] == 'connectWiFi':
                ssid = config.get("ssid")
                if "password" in config:
                    password = config.get("password")
                else:
                    password = ""
                ip_address = self.connect_to_wifi(ssid, password)
                if ip_address:
                    output["status"] = "success"
                    output["ip"] = ip_address
                    self.status_display.display_header_and_status(header="System Config", status="Wi-Fi Connected")
                else:
                    output["status"] = "failed"
                    self.status_display.display_header_and_status(header="System Config", status="Failed")

            # Get MAC address
            elif config["type"] == 'getMAC':
                mac_address = self.get_mac_address()
                if mac_address:
                    output['status'] = 'success'
                    output['mac'] = mac_address
                    self.status_display.display_header_and_status(header="System Config", status="MAC Obtained")
                else:
                    output['status'] = 'failed'
                    self.status_display.display_header_and_status(header="System Config", status="Failed")

            # Get all logs
            elif config["type"] == 'getLogs':
                self.get_logs()
                output['status'] = 'success'
                output['message'] = 'Logs copied successfully'
                self.status_display.display_header_and_status(header="System Config", status="Logs Copied")

            # Unknown
            elif config["type"] == 'unknown':
                output['status'] = 'failed'
                output["message"] = f"Unknown type - {config['type']}"
                self.status_display.display_header_and_status(header="System Config", status="Unknown Config Type")

            # Write the output
            with open(output_file, 'w') as f:
                json.dump(output, f)
            time.sleep(2)
            self.logger.info("System configuration parsed successfully")

        except Exception as e:
            self.status_display.display_header_and_status(header="System Config", status="Exception occurred")
            self.logger.error(f"Error getting system configuration: {e}")

        finally:
            # Clean up
            if os.path.exists(system_config_file):
                os.remove(system_config_file)
