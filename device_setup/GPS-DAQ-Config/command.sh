#!/bin/bash

#####################################################################
# Configure Device
#####################################################################

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

# Enable SPI interface
# TODO: Sometimes SPI could be commented
if ! grep -q "^dtparam=spi=on" /boot/firmware/config.txt; then
  echo "Enabling SPI interface."
  echo "dtparam=spi=on" | sudo tee -a /boot/firmware/config.txt
else
  echo "SPI interface is already enabled."
fi

# Enable I2C0 for display
if ! grep -q "^dtparam=i2c0=on" /boot/firmware/config.txt; then
  echo "Enabling I2C0 interface."
  echo "dtparam=i2c0=on" | sudo tee -a /boot/firmware/config.txt
else
  echo "I2C0 interface is already enabled."
fi

#####################################################################
# Install Required Packages
#####################################################################

# GPS
# Get the GPSD module
sudo apt-get update -y
sudo apt-get upgrade -y
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
# Enable autostart
sudo systemctl enable gpsd.socket
sudo systemctl start gpsd.socket

# Python and Pip
sudo apt-get install python3 python3-pip
# OLED display
sudo apt-get install git
pushd /home/minlab || { echo "Can't find directory /home/minlab"; exit 1; }
git clone https://github.com/rm-hull/luma.examples.git
pushd /home/minlab/luma.examples || { echo "Clone of OLED repository failed"; exit 1; }
sudo -H pip install -e . --break-system-packages
# psutil
sudo pip install psutil --break-system-packages


#####################################################################
# Configuring USB auto-mount and auto-unmount
#####################################################################

###########################
# Auto-mount
###########################
# Create a mount script
cat << 'EOF' | sudo tee /root/mount-usb.sh > /dev/null
#!/bin/bash

LOGFILE="/var/log/mount-usb.log"
MOUNT_POINT="/mnt/data"

echo "$(date) - Mount script started" >> $LOGFILE

# Create the mount point directory if it doesn't exist
[ -d "$MOUNT_POINT" ] || mkdir -p "$MOUNT_POINT"

# Get the device name from the environment variable passed by udev
DEVICE="/dev/$1"

# Log the device name
echo "$(date) - Device: $DEVICE" >> $LOGFILE

# Mount the device
mount -o noatime "$DEVICE" "$MOUNT_POINT" >> $LOGFILE 2>&1

# Log the mount status
if mountpoint -q "$MOUNT_POINT"; then
    echo "$(date) - Mount successful" >> $LOGFILE
else
    echo "$(date) - Mount failed" >> $LOGFILE
fi
EOF
# Make executable
sudo chmod +x /root/mount-usb.sh

# Create systemd service for mount
cat << 'EOF' | sudo tee /etc/systemd/system/mount-usb@.service
[Unit]
Description=Mount USB Drive
After=dev-%i.device

[Service]
Type=oneshot
ExecStart=/root/mount-usb.sh %I

[Install]
WantedBy=multi-user.target
EOF

# Create the udev rule
cat <<'EOF' | sudo tee /etc/udev/rules.d/99-usb-mount.rules > /dev/null
ACTION=="add", SUBSYSTEM=="block", KERNEL=="sd[a-z][0-9]", ENV{SYSTEMD_WANTS}="mount-usb@%k.service"
EOF

###########################
# Auto-unmount
###########################
# Create the unmount script
cat <<'EOF' | sudo tee /root/unmount-usb.sh > /dev/null
#!/bin/bash

LOGFILE="/var/log/unmount-usb.log"
MOUNT_POINT="/mnt/data"

echo "$(date) - Unmount script started" >> $LOGFILE

# Unmount the device
umount "$MOUNT_POINT" >> $LOGFILE 2>&1

# Log the unmount status
if mountpoint -q "$MOUNT_POINT"; then
    echo "$(date) - Unmount failed" >> $LOGFILE
else
    echo "$(date) - Unmount successful" >> $LOGFILE
fi

echo "$(date) - Unmount script finished" >> $LOGFILE
EOF
# Make the unmount script executable
sudo chmod +x /root/unmount-usb.sh

# Create the systemd service
cat <<'EOF' | sudo tee /etc/systemd/system/unmount-usb.service > /dev/null
[Unit]
Description=Unmount USB Drive

[Service]
Type=oneshot
ExecStart=/root/unmount-usb.sh

[Install]
WantedBy=multi-user.target
EOF

# Create the udev rule
cat <<'EOF' | sudo tee /etc/udev/rules.d/99-usb-unmount.rules > /dev/null
ACTION=="remove", SUBSYSTEM=="block", KERNEL=="sd[a-z][0-9]", RUN+="/bin/systemctl start unmount-usb.service"
EOF

# Reload changes
# Reload systemd configuration
sudo systemctl daemon-reload
# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger


# Reboot the device
echo "Rebooting the system to apply changes..."
sleep 5
sudo reboot now