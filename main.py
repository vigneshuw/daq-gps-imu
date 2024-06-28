import time
from signal import pause
from IMU.device import IMUPoller
from gpsdevice import GPSPoller, GPSCommandSender
from button import ButtonHandler


# # Configure GPS device
# gpsc = GPSCommandSender(baudrate=9600)
# # Update GPS DAQ params
# gpsc.send_command("rate-10")
# time.sleep(1)
# gpsc.send_command("baud-115200")
# # Initialize DAQ
# gpsp = GPSPoller()
#
#
# # Callbacks for data collection
# def start_daq():
#     gpsp.start_polling()
#
#
# def stop_daq():
#     gpsp.stop_polling()
#
#
# # Setup buttons
# button_daq = ButtonHandler(pin=16, on_button_held_callback=start_daq, on_button_released_callback=stop_daq,
#                            press_duration=5)


if __name__ == '__main__':
    imu_poller = IMUPoller()
    if imu_poller.start_polling():
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            imu_poller.stop_polling()
