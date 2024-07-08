#!/bin/bash

# Define variables
UPDATE_FILE="__drivesense_fwupdate.tar"
UPDATE_DIR="drivesense_update"
TARGET_DIR="/opt/drivesense"
DRIVESENSE_FILE="drivesense"


# Check if the update file exists
if [ -f "$UPDATE_FILE" ]; then
    echo "Update file found: $UPDATE_FILE"

    # Create a temporary directory for the update
    mkdir -p "$UPDATE_DIR"

    # Extract the update file
    tar -xvf "$UPDATE_FILE" -C "$UPDATE_DIR"

    # Check if the drivesense file exists in the extracted content
    if [ -f "$UPDATE_DIR/$DRIVESENSE_FILE" ]; then
        echo "drivesense file found. Updating..."

        # Copy the drivesense file to the target location
        cp "$UPDATE_DIR/$DRIVESENSE_FILE" "$TARGET_DIR/"

        # Clean up the temporary update directory
        rm -rf "$UPDATE_DIR"

        # Remove the update file
        rm -f "$UPDATE_FILE"

        echo "Update successful!"
    else
        echo "Error: drivesense file not found in the update package."

        # Clean up the temporary update directory
        rm -rf "$UPDATE_DIR"

        # Remove the update file
        rm -f "$UPDATE_FILE"
    fi
else
    echo "Error: Update file $UPDATE_FILE not found."
fi