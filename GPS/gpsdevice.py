import os
import sys
import subprocess
import gps
import threading
import time
import pickle
import json
import serial
import logging


class GPSPoller(threading.Thread):

    def __init__(self, save_dir_time):
        threading.Thread.__init__(self)

        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)

        # Configure the GPS unit
        self.logger.info("Configuring GPS for BAUD of 115200 and rate of 10Hz")
        gpsc = GPSCommandSender(baudrate=9600)
        # Update GPS DAQ params
        gpsc.send_command("rate-10")
        time.sleep(1)
        gpsc.send_command("baud-115200")

        self.gpsd = gps.gps(mode=gps.WATCH_ENABLE)
        self.running = False

        # Time Management
        self.start_time = None
        self.stop_time = None
        self.save_dir_time = save_dir_time

        # Metadata
        self.current_save_dir = None
        self.metadata = {}

    def run(self):
        self.start_time = time.time()
        self.metadata["start_time"] = self.start_time

        # Make directories
        self.current_save_dir = "/sensor_data" + "/" + self.save_dir_time
        if not os.path.exists(self.current_save_dir):
            os.makedirs(self.current_save_dir)

        self.logger.info("Starting GPS DAQ")
        with open(self.current_save_dir + "/" + "gps.dat", "wb") as fh:
            while self.running:
                gps_info = self.gpsd.next()
                # Serialize and store data
                pickle.dump(gps_info, fh, protocol=pickle.HIGHEST_PROTOCOL)
        self.logger.info("Stopping GPS DAQ")

    def start_polling(self):
        if not self.running:
            self.running = True
            self.start()

    def stop_polling(self):
        if self.running:
            self.running = False
            self.stop_time = time.time()
            self.metadata["stop_time"] = self.stop_time

            self.join()

            # Write the metadata
            with open(self.current_save_dir + "/" + "gps.meta", "w") as fh:
                json_string = json.dumps(self.metadata)
                fh.write(json_string + "\n")

    def stop(self):
        self.running = False


class GPSCommandSender:
    def __init__(self, port="/dev/serial0", baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = serial.Serial(port, baudrate, timeout=5)

    def send_command(self, ctype: str):

        # Determine based on command type
        if ctype == "reset":
            command = b"\xb5\x62\x06\x04\x04\x00\xff\xff\x02\x00\x0e\x61"
        elif ctype == "rate-2":
            command = b"\xB5\x62\x06\x08\x06\x00\xF4\x01\x01\x00\x01\x00\x0B\x77"
        elif ctype == "rate-5":
            command = b"\xB5\x62\x06\x08\x06\x00\xC8\x00\x01\x00\x01\x00\xDE\x6A"
        elif ctype == "rate-10":
            command = b"\xB5\x62\x06\x08\x06\x00\x64\x00\x01\x00\x01\x00\x7A\x12"
        elif ctype == "baud-115200":
            command = b"\xB5\x62\x06\x00\x14\x00\x01\x00\x00\x00\xD0\x08\x00\x00\x00\xC2\x01\x00\x07\x00\x03\x00\x00\x00\x00\x00\xC0\x7E"
        elif ctype == "baud-9600":
            command = b"\xB5\x62\x06\x00\x14\x00\x01\x00\x00\x00\xD0\x08\x00\x00\x80\x25\x00\x00\x07\x00\x03\x00\x00\x00\x00\x00\xA2\xB5"
        elif ctype == "sleep":
            command = b"\xB5\x62\x06\x57\x08\x00\x01\x00\x00\x00\x50\x4F\x54\x53\xAC\x85"
        elif ctype == "wake":
            command = b"\xB5\x62\x06\x57\x08\x00\x01\x00\x00\x00\x20\x4E\x55\x52\x7B\xC3"
        else:
            sys.stdout.write(ctype + " is not supported for sending commands\n")
            return

        try:
            self.stop_gpsd()

            if not self.ser.is_open:
                self.ser.open()
            self.ser.write(command)
        finally:
            self.start_gpsd()

    def stop_gpsd(self):
        """
        Stop gpsd service and socket

        :return: None
        """
        subprocess.run(["sudo", "systemctl", "stop", "gpsd.socket"])
        subprocess.run(["sudo", "systemctl", "stop", "gpsd"])

    def start_gpsd(self):
        """
        Start gpsd service and socket

        :return: None
        """
        subprocess.run(["sudo", "systemctl", "start", "gpsd.socket"])
        subprocess.run(["sudo", "systemctl", "start", "gpsd"])

    def close(self):
        if self.ser.is_open:
            self.ser.close()


