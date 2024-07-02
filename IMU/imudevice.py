import json
import sys
import threading
import time
import os
import struct
import RPi.GPIO as GPIO
from queue import Queue
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

                self.data_queue.put(f"{gx},{gy},{gz},{ax_g},{ay_g},{az_g}\n")
                print(f"Acceleration - X: {ax_g:.6f} g, Y: {ay_g:.6f} g, Z: {az_g:.6f} g")

    def run(self):
        self.start_time = time.time()
        self.metadata["start_time"] = self.start_time

        while self.running:
            if GPIO.input(self.imu_device.drdy_pin) == GPIO.HIGH:
                self.data_ready_callback()

    def start_polling(self):
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
                sys.stdout.write("IMU Device not detected. DAQ Process not started\n")
                return False

    def stop_polling(self):
        if self.running:
            self.running = False

            # Stop the DAQ process
            self.imu_device.close()
            self.stop_time = time.time()
            self.metadata["stop_time"] = self.stop_time

            # Start the file save process
            # Make directories
            self.current_save_dir = "/sensor_data" + "/" + self.save_dir_time
            if not os.path.exists(self.current_save_dir):
                os.makedirs(self.current_save_dir)

            # Write the metadata
            with open(self.current_save_dir + "/" + "imu.meta", "w") as fh:
                json_string = json.dumps(self.metadata)
                fh.write(json_string + "\n")

            self.join()

            # Write all the queued up data
            output_file = os.path.join(self.current_save_dir, "imu.dat")
            # Create file with headers
            with open(output_file, "w") as fh:
                fh.write("gx,gy,gz,ax_g,ay_g,az_g\n")
                while not self.data_queue.empty():
                    fh.write(self.data_queue.get())
                fh.flush()
