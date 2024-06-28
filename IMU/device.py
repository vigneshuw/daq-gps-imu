import json
import sys
import threading
import time
import os
import pickle
from queue import Queue
from IMU.lsm6dsl import LSM6DSL

# lsm6dsl = LSM6DSL()
# # Initialize device
# lsm6dsl.open()
# lsm6dsl.configure_sensor()
# lsm6dsl.detect_device()
#
# try:
#     while True:
#         gyro_data, accel_data = lsm6dsl.read_gyro_accel()
#         gx, gy, gz = gyro_data
#         ax, ay, az = accel_data
#
#         # Convert to signed values (already handled by struct.unpack)
#         # Convert raw accelerometer values to g's (assuming full-scale range of ±2g)
#         ax_g = ax * 0.000488
#         ay_g = ay * 0.000488
#         az_g = az * 0.000488
#
#         # print(f"Gyroscope - X: {gx}, Y: {gy}, Z: {gz}")
#         print(f"Acceleration - X: {ax_g:.6f} g, Y: {ay_g:.6f} g, Z: {az_g:.6f} g")
#
#         time.sleep(1 / 3300)  # Sleep for the period of 3.3 kHz sampling rate
#
# except KeyboardInterrupt:
#     print("\nExiting...")
# finally:
#     lsm6dsl.close()


class IMUPoller(threading.Thread):
    def __init__(self, bus=0, device=0, max_speed_hz=10000000, drdy_pin=24):
        threading.Thread.__init__(self)
        self.imu_device = LSM6DSL(spi_bus=bus, spi_dev=device, speed=max_speed_hz, drdy_pin=drdy_pin)

        self.running = False
        self.data_queue = Queue()
        self.file_writer_thread = None

        # Time Management
        self.start_time = None
        self.stop_time = None

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
        print(f"Acceleration - X: {ax_g:.6f} g, Y: {ay_g:.6f} g, Z: {az_g:.6f} g")

    def run(self):
        self.start_time = time.time()
        self.metadata["start_time"] = self.start_time

        # Make directories
        self.current_save_dir = "/sensor_data" + "/" + str(round(self.start_time))
        if not os.path.exists(self.current_save_dir):
            os.makedirs(self.current_save_dir)
        output_file = os.path.join(self.current_save_dir, "imu.dat")

        # Create file with headers
        with open(output_file, "w") as fh:
            fh.write("gx,gy,gz,ax_g,ay_g,az_g\n")

        # Start the writing file thread
        self.file_writer_thread = FileWriter(self.data_queue, output_file)
        self.file_writer_thread.start()

        while self.running:
            if self.imu_device.line.get_value() == 1:
                self.data_ready_callback()

        self.file_writer_thread.stop()

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


class FileWriter(threading.Thread):
    def __init__(self, data_queue, output_file, write_interval=60):
        threading.Thread.__init__(self)
        self.data_queue = data_queue
        self.output_file = output_file
        self.running = True
        self.write_interval = write_interval

    def run(self):
        with open(self.output_file, "a") as fh:
            while self.running:
                time.sleep(self.write_interval)
                while not self.data_queue.empty():
                    fh.write(self.data_queue.get())
                fh.flush()

    def stop(self):
        self.running = False
