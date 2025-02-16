import json
import sys
import threading
import time
import os
import struct
import logging
import RPi.GPIO as GPIO
from queue import Queue
import utils
from IMU import lsm6dsl


class IMUPoller(threading.Thread):
    def __init__(self, save_dir_time, bus=0, device=0, max_speed_hz=10000000, drdy_pin=24):
        threading.Thread.__init__(self)
        self.file_writer_thread = None
        self.imu_device = lsm6dsl.LSM6DSL(spi_bus=bus, spi_dev=device, speed=max_speed_hz, drdy_pin=drdy_pin)

        self.running = False
        self.data_queue = Queue()

        # Time Management
        self.start_time = None
        self.stop_time = None
        self.save_dir_time = save_dir_time

        # Metadata
        self.current_save_dir = None
        self.metadata = {}

        # Logging
        self.logger = logging.getLogger(self.__class__.__name__)

    def data_ready_callback(self):
        """
        Queries the sensor data from FIFO and adds to a queue

        :return: None
        """

        status1, status2, status3, status4 = self.imu_device.read_fifo_status()
        num_words = (status2 & 0x0F) << 8 | status1

        if num_words > 0:
            fifo_data = self.imu_device.read_fifo_data(num_words)

            for i in range(0, len(fifo_data), 12):
                gx = struct.unpack('<h', bytes(fifo_data[i:i + 2]))[0]
                gy = struct.unpack('<h', bytes(fifo_data[i + 2:i + 4]))[0]
                gz = struct.unpack('<h', bytes(fifo_data[i + 4:i + 6]))[0]
                ax = struct.unpack('<h', bytes(fifo_data[i + 6:i + 8]))[0]
                ay = struct.unpack('<h', bytes(fifo_data[i + 8:i + 10]))[0]
                az = struct.unpack('<h', bytes(fifo_data[i + 10:i + 12]))[0]

                ax_g = ax * 0.000488
                ay_g = ay * 0.000488
                az_g = az * 0.000488

                self.data_queue.put(f"{gx},{gy},{gz},{round(ax_g, 4)},{round(ay_g, 4)},{round(az_g, 4)}\n".encode())
                # print(f"Acceleration - X: {ax_g:.6f} g, Y: {ay_g:.6f} g, Z: {az_g:.6f} g")

    def run(self):
        """
        Start the thread responsible for IMU data collection

        :return: None
        """

        self.start_time = time.monotonic()

        # Saving the data periodically - Make directories
        self.current_save_dir = "/sensor_data" + "/" + self.save_dir_time
        if not os.path.exists(self.current_save_dir):
            os.makedirs(self.current_save_dir)
        output_file = os.path.join(self.current_save_dir, "imu.dat")

        # Create file with headers
        with open(output_file, "w") as fh:
            fh.write("gx,gy,gz,ax_g,ay_g,az_g\n")

        # Start the writing file thread
        self.file_writer_thread = threading.Thread(target=utils.file_writer, args=(self.data_queue, output_file))
        self.file_writer_thread.start()

        self.logger.info("Starting IMU DAQ")
        while self.running:
            if GPIO.input(self.imu_device.drdy_pin) == GPIO.HIGH:
                self.data_ready_callback()
        self.logger.info("Stopping IMU DAQ")

        self.data_queue.put(None)
        self.file_writer_thread.join()

    def start_polling(self):
        """
        Start the DAQ process if all conditions are met

        :return: None
        """

        if not self.running:
            # Configure sensor and initiate
            self.imu_device.open()
            time.sleep(1)
            self.running = self.imu_device.detect_device()
            if self.running:
                self.start()
                self.imu_device.configure_sensor()
                return True
            else:
                self.logger.error("IMU Device not detected. DAQ Process not started")
                return False

    def stop_polling(self):
        """
        Stop the DAQ process if it is running

        :return: None
        """

        if self.running:
            self.running = False

            # Stop the DAQ process
            self.stop_time = time.monotonic()
            self.metadata["elapsed_time"] = self.stop_time - self.start_time

            # Stop the DAQ
            self.join()

            # Write the metadata
            with open(self.current_save_dir + "/" + "imu.meta", "w") as fh:
                json_string = json.dumps(self.metadata)
                fh.write(json_string + "\n")

            self.imu_device.close()
