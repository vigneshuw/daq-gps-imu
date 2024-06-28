#!/bin/bash

# Remove the serial console
sudo sed -i 's/console=serial0,[0-9]\+ //g' /boot/firmware/cmdline.txt
sudo sed -i 's/console=ttyAMA0,[0-9]\+ //g' /boot/firmware/cmdline.txt

# Keep the hardware to be enabled
if grep -q "dtparam=uart0=on" /boot/firmware/config.txt; then
    echo "UART is already enabled."
else
    echo "Enabling UART."
    echo "dtparam=uart0=on" | sudo tee -a /boot/firmware/config.txt
fi

# For Raspberry Pi 5 specific devices
if grep -q "Raspberry Pi 5" /proc/device-tree/model; then
  grep -q "dtparam=uart0_console" /boot/firmware/config.txt || echo "dtparam=uart0_console" | sudo tee -a /boot/firmware/config.txt
  echo "Raspberry Pi 5 detected. The specific configuration added"
else
  echo "Device is not Raspberry Pi 5. Skipping device specific configuration"
fi

# Get the GPSD module
sudo apt-get install gpsd-clients gpsd -y
sudo killall gpsd

# Increase BAUDRATE and Configure GPSD
GPSD_CONFIG="/etc/default/gpsd"
if grep -q '^DEVICES=""$' "$GPSD_CONFIG"; then
    sudo sed -i 's|^DEVICES=""$|DEVICES="/dev/serial0"|' "$GPSD_CONFIG"
elif ! grep -q '^DEVICES="/dev/serial0"$' "$GPSD_CONFIG"; then
    echo 'DEVICES="/dev/serial0"' | sudo tee -a "$GPSD_CONFIG"
fi
if grep -q '^GPSD_OPTIONS=.*$' "$GPSD_CONFIG"; then
    sudo sed -i 's|^GPSD_OPTIONS=.*$|GPSD_OPTIONS="--speed 115200"|' "$GPSD_CONFIG"
else
    echo 'GPSD_OPTIONS="--speed 115200"' | sudo tee -a "$GPSD_CONFIG"
fi

# Enable SPI interface
if ! grep -q "^dtparam=spi=on" /boot/firmware/config.txt; then
  echo "Enabling SPI interface."
  echo "dtparam=spi=on" | sudo tee -a /boot/firmware/config.txt
else
  echo "SPI interface is already enabled."
fi

# Enable autostart
sudo systemctl enable gpsd.socket
sudo systemctl start gpsd.socket

# Reboot the device
echo "Rebooting the system to apply changes..."
sleep 5
sudo reboot now