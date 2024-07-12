import spidev
import struct
import RPi.GPIO as GPIO
import time
import sys
import logging


class LSM6DSL:
    # Find device
    WHO_AM_I = 0x0F

    # Control
    CTRL1_XL = 0x10
    CTRL2_G = 0x11
    CTRL3_C = 0x12
    CTRL4_C = 0x13
    CTRL8_XL = 0x17

    # Data Registers
    OUTX_L_G = 0x22
    OUTX_H_G = 0x23
    OUTY_L_G = 0x24
    OUTY_H_G = 0x25
    OUTZ_L_G = 0x26
    OUTZ_H_G = 0x27
    OUTX_L_XL = 0x28
    OUTX_H_XL = 0x29
    OUTY_L_XL = 0x2A
    OUTY_H_XL = 0x2B
    OUTZ_L_XL = 0x2C
    OUTZ_H_XL = 0x2D

    # Start DAQ
    CTRL9_XL = 0x18
    CTRL10_C = 0x19

    # INT2
    INT2_CTRL = 0x0E

    # FIFO
    # Control
    FIFO_CTRL1 = 0x06
    FIFO_CTRL2 = 0x07
    FIFO_CTRL3 = 0x08
    FIFO_CTRL4 = 0x09
    FIFO_CTRL5 = 0x0A
    # Status
    FIFO_STATUS1 = 0x3A
    FIFO_STATUS2 = 0x3B
    FIFO_STATUS3 = 0x3C
    FIFO_STATUS4 = 0x3D
    # Data Read
    FIFO_DATA_OUT_L = 0x3E
    FIFO_DATA_OUT_H = 0x3F

    def __init__(self, spi_bus=0, spi_dev=0, speed=10000000, drdy_pin=24):
        # Initialization
        self.spi_bus = spi_bus
        self.spi_dev = spi_dev
        self.speed = speed
        self.spi = spidev.SpiDev()

        # Logging
        self.logger = logging.getLogger(self.__class__.__name__)

        # GPIO setup for data ready pin
        self.drdy_pin = drdy_pin
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.drdy_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        except RuntimeError as e:
            self.logger.error(f"Error setting up GPIO: {e}")
            sys.exit(1)

    def open(self):
        """
        Setup SPI for device communication

        :return: None
        """

        self.spi.open(self.spi_bus, self.spi_dev)
        self.spi.max_speed_hz = self.speed
        self.spi.mode = 0b11

    def write_register(self, register, value):
        """
        Write to a register

        :param register: The register to write
        :param value: A byte value to write
        :return: Write status
        """

        rx = self.spi.xfer2([register & 0x7F, value])
        return rx

    def read_register(self, register):
        """
        Read a single byte from a register

        :param register: The register to read from.
        :return: The read byte value
        """

        rx = self.spi.xfer2([register | 0x80, 0x00])
        return rx[1]

    def configure_sensor(self):
        """
        Configure the IMU sensor in the BerryGPS-IMU v4 device

        :return: None
        """

        # Reset device
        self.write_register(self.CTRL3_C, 0x01)     # SW Reset
        time.sleep(0.1)

        # Initialize the sensor
        self.write_register(self.CTRL1_XL, 0x77)     # ODR 0.83 kHz, +/- 16g, BW=400Hz
        self.write_register(self.CTRL8_XL, 0xC8)     # Low pass filter enabled, BW9, composite filter
        self.write_register(self.CTRL2_G, 0x7C)      # ODR 0.83 kHz, 2000 dps
        self.write_register(self.CTRL3_C, 0x44)      # BDU=1, IF_INC=1
        self.write_register(self.CTRL4_C, 0x04)      # Enable data-ready interrupt

        # Enable accelerometer and gyroscope
        self.write_register(self.CTRL9_XL, 0x38)  # Enable X, Y, Z axes of accelerometer
        self.write_register(self.CTRL10_C, 0x38)  # Enable X, Y, Z axes of gyroscope

        # Configure FIFO Control
        self.write_register(self.FIFO_CTRL1, 0x80)
        self.write_register(self.FIFO_CTRL2, 0x07)
        self.write_register(self.FIFO_CTRL3, 0x09)
        self.write_register(self.FIFO_CTRL4, 0x00)
        self.write_register(self.FIFO_CTRL5, 0x3E)

        # Data ready interrupt
        self.write_register(self.INT2_CTRL, 0x08)

    def read_bulk_data(self):
        """
        Read a bulk of 12 bytes from SPI on the BerryGPS-IMU v4 device spanning across accelerometer and gyroscope

        :return: A list of read byte values
        """

        raw_data = self.spi.xfer2([self.OUTX_L_G | 0x80] + [0x00] * 12)[1:]
        return raw_data

    def read_gyro_accel(self):
        """
        Do a bulk read on the acceleration and gyroscope sensor on the BerryGPS-IMU v4 device

        :return: A tuple of two tuples, containing the acceleration and gyroscope sensor values for three axis
        """

        raw_data = self.read_bulk_data()

        gx = struct.unpack('<h', bytes(raw_data[0:2]))[0]
        gy = struct.unpack('<h', bytes(raw_data[2:4]))[0]
        gz = struct.unpack('<h', bytes(raw_data[4:6]))[0]
        ax = struct.unpack('<h', bytes(raw_data[6:8]))[0]
        ay = struct.unpack('<h', bytes(raw_data[8:10]))[0]
        az = struct.unpack('<h', bytes(raw_data[10:12]))[0]

        return (gx, gy, gz), (ax, ay, az)

    def read_fifo_status(self):
        """
        Read four status values for the FIFO

        :return: A tuple of four status values
        """

        status1 = self.read_register(self.FIFO_STATUS1)
        status2 = self.read_register(self.FIFO_STATUS2)
        status3 = self.read_register(self.FIFO_STATUS3)
        status4 = self.read_register(self.FIFO_STATUS4)
        return status1, status2, status3, status4

    def read_fifo_data(self, num_words):
        """
        Read data from the FIFO buffer for the device.

        :param num_words: Number of words to read from the FIFO buffer.
        :return: The read data in a list
        """

        num_bytes = num_words * 2
        return self.spi.xfer2([self.FIFO_DATA_OUT_L | 0x80] + [0x00] * num_bytes)[1:]

    def read_fifo_word(self):
        """
        Read a FIFO word from the FIFO buffer.

        :return: A list containing the word (2 bytes)
        """

        return self.spi.xfer2([self.FIFO_DATA_OUT_L | 0x80, 0x00, 0x00])[1:]

    def close(self):
        """
        Close the SPI communication and cleanup

        :return:
        """

        # TODO: Disable the data collection for the device
        self.spi.close()
        GPIO.cleanup(self.drdy_pin)

    def detect_device(self):
        """
        Detect to see if the IMU device is reachable over SPI

        :return: True, if the device is accessible
        """

        try:
            response = self.read_register(self.WHO_AM_I)
        except IOError as e:
            self.logger.error(f"Failed to connect to IMU over SPI: {e}")
            return False
        else:
            if response == 0x6A:
                self.logger.info(f"Found BerryGPS-IMU device, Response: {response}")
                return True

        return False
