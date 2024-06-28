import spidev
import struct
import gpiod
import time


class LSM6DSL:
    # Find device
    WHO_AM_I = 0x0F

    # Control
    CTRL1_XL = 0x10
    CTRL2_G = 0x11
    CTRL3_C = 0x12
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

    def __init__(self, spi_bus=0, spi_dev=0, speed=10000000, drdy_pin=24):
        # Initialization
        self.spi_bus = spi_bus
        self.spi_dev = spi_dev
        self.speed = speed
        self.spi = spidev.SpiDev()

        # GPIO setup for data ready pin
        self.drdy_pin = drdy_pin
        self.chip = gpiod.Chip('gpiochip4', gpiod.Chip.OPEN_BY_NAME)
        self.line = self.chip.get_line(self.drdy_pin)
        self.line.request(consumer="LSM6DSL", type=gpiod.LINE_REQ_DIR_IN)

    def open(self):
        self.spi.open(self.spi_bus, self.spi_dev)
        self.spi.max_speed_hz = self.speed
        self.spi.mode = 0b11

    def write_register(self, register, value):
        rx = self.spi.xfer2([register & 0x7F, value])
        return rx

    def read_register(self, register):
        rx = self.spi.xfer2([register | 0x80, 0x00])
        return rx[1]

    def configure_sensor(self):

        # Reset device
        self.write_register(self.CTRL3_C, 0x01)     # SW Reset
        time.sleep(0.1)

        # Initialize the sensor
        self.write_register(self.CTRL1_XL, 0x97)     # ODR 3.33 kHz, +/- 16g, BW=400Hz
        self.write_register(self.CTRL8_XL, 0xC8)     # Low pass filter enabled, BW9, composite filter
        self.write_register(self.CTRL2_G, 0x9C)      # ODR 3.3 kHz, 2000 dps
        self.write_register(self.CTRL3_C, 0x44)      # BDU=1, IF_INC=1

        # Enable accelerometer and gyroscope
        self.write_register(self.CTRL9_XL, 0x38)  # Enable X, Y, Z axes of accelerometer
        self.write_register(self.CTRL10_C, 0x38)  # Enable X, Y, Z axes of gyroscope

        # Data ready interrupt
        self.write_register(self.INT2_CTRL, 0x03)

    def read_bulk_data(self):

        raw_data = self.spi.xfer2([self.OUTX_L_G | 0x80] + [0x00] * 12)[1:]
        return raw_data

    def read_gyro_accel(self):
        raw_data = self.read_bulk_data()

        gx = struct.unpack('<h', bytes(raw_data[0:2]))[0]
        gy = struct.unpack('<h', bytes(raw_data[2:4]))[0]
        gz = struct.unpack('<h', bytes(raw_data[4:6]))[0]
        ax = struct.unpack('<h', bytes(raw_data[6:8]))[0]
        ay = struct.unpack('<h', bytes(raw_data[8:10]))[0]
        az = struct.unpack('<h', bytes(raw_data[10:12]))[0]

        return (gx, gy, gz), (ax, ay, az)

    def close(self):
        self.spi.close()
        self.line.release()

    def detect_device(self):

        try:
            response = self.read_register(self.WHO_AM_I)
        except IOError as e:
            print(e)
            return False
        else:
            if response == 0x6A:
                print(f"Found BerryGPS-IMU device, Response: {response}")
                return True

        return False
