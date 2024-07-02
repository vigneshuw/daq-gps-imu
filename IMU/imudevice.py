import json
import sys
import multiprocessing as mp
import threading
import time
import os
import utils
from queue import Queue
import RPi.GPIO as GPIO
from . import lsm6dsl


class IMUPoller(threading.Thread):
    def __init__(self, save_dir_time, bus=0, device=0, max_speed_hz=10000000, drdy_pin=24):
        threading.Thread.__init__(self)
        self.imu_device = lsm6dsl.LSM6DSL(spi_bus=bus, spi_dev=device, speed=max_speed_hz, drdy_pin=drdy_pin)

        self.running = False
        self.data_queue = Queue()
        self.file_writer_process = None

        # Time Management
        self.start_time = None
        self.stop_time = None
        self.save_dir_time = save_dir_time

        # Metadata
        self.current_save_dir = None
        self.metadata = {}

    def data_ready_callback(self):
        gyro_data, accel_data = self.imu_device.read_gyro_accel()
        gx, gy, gz = gyro_data
        ax, ay, az = accel_data

        # Convert to human readable values
        ax_g = ax * 0.000488
        ay_g = ay * 0.000488
        az_g = az * 0.000488

        # Store data in queue
        self.data_queue.put(f"{gx},{gy},{gz},{ax_g},{ay_g},{az_g}\n")
        # print(f"Acceleration - X: {ax_g:.6f} g, Y: {ay_g:.6f} g, Z: {az_g:.6f} g")

    def run(self):
        self.start_time = time.time()
        self.metadata["start_time"] = self.start_time

        # Make directories
        self.current_save_dir = "/sensor_data" + "/" + self.save_dir_time
        if not os.path.exists(self.current_save_dir):
            os.makedirs(self.current_save_dir)
        output_file = os.path.join(self.current_save_dir, "imu.dat")

        # Create file with headers
        with open(output_file, "w") as fh:
            fh.write("gx,gy,gz,ax_g,ay_g,az_g\n")

        # Start the writing file thread
        self.file_writer_process = mp.Process(target=utils.file_writer, args=(self.data_queue, output_file))
        self.file_writer_process.start()

        while self.running:
            if GPIO.input(self.imu_device.drdy_pin) == GPIO.HIGH:
                self.data_ready_callback()

        self.file_writer_process.terminate()

    def start_polling(self):
        if not self.running:
            # Configure sensor and initiate
            self.imu_device.open()
            self.imu_device.configure_sensor()
            time.sleep(1)
            self.running = self.imu_device.detect_device()
            if self.running:
                self.start()
                return True
            else:
                sys.stdout.write("IMU Device not detected. DAQ Process not started\n")
                return False

    def stop_polling(self):
        if self.running:
            self.running = False

            # Stop the DAQ process
            self.imu_device.close()

            self.stop_time = time.time()
            self.metadata["stop_time"] = self.stop_time

            # Write the metadata
            with open(self.current_save_dir + "/" + "imu.meta", "w") as fh:
                json_string = json.dumps(self.metadata)
                fh.write(json_string + "\n")

            self.join()
