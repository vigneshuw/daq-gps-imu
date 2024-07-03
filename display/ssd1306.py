import os
import psutil
import subprocess
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont


class Display:

    def __init__(self, i2c_port=0, address=0x3C, logo_loc=None):

        # Create device
        serial = i2c(port=i2c_port, address=address)
        self.device = ssd1306(serial)
        self.font = ImageFont.truetype('DejaVuSans.ttf', 11)
        self.font_large = ImageFont.truetype('DejaVuSans-Bold.ttf', 14)

        # Default items
        self.logo_location = logo_loc

    def get_canvas(self):
        return canvas(self.device)

    def get_system_properties(self):
        # Get SD card remaining memory
        st = os.statvfs('/')
        free_memory = (st.f_bavail * st.f_frsize) / 1024 / 1024 / 1000  # Convert to GB

        # Get RAM usage
        ram = psutil.virtual_memory()
        ram_free = ram.available / 1024 / 1024 / 1000  # Convert to GB

        # Get CPU clock frequency
        clock_freq = subprocess.check_output(
            "vcgencmd measure_clock arm", shell=True).decode('utf-8')
        clock_freq = int(clock_freq.split('=')[1].strip()) / 1e9  # Convert to GHz

        # Get CPU temperature
        cpu_temp = subprocess.check_output(
            "vcgencmd measure_temp", shell=True).decode('utf-8')
        cpu_temp = float(cpu_temp.split('=')[1].split("'")[0])  # Extract temperature

        return free_memory, ram_free, clock_freq, cpu_temp

    def display_default_image(self):
        if self.logo_location is not None:
            self.display_image(self.logo_location)

    def display_system_props(self):
        # Get the logo
        logo = Image.open(self.logo_location).convert('RGBA')

        # Resize the image, ensuring the aspect ratio
        # Original dimensions
        orig_width, orig_height = logo.size
        # Desired dimensions
        max_width, max_height = self.device.width // 2, self.device.height
        # Aspect ratio
        aspect_ratio = orig_width / orig_height

        # Determine new dimensions
        if (max_width / aspect_ratio) <= max_height:
            new_width = max_width
            new_height = int(max_width / aspect_ratio)
        else:
            new_height = max_height
            new_width = int(max_height * aspect_ratio)

        # Resize image maintaining aspect ratio
        logo = logo.resize((new_width, new_height))

        # Create a new blank image with the display size
        final_image = Image.new('1', (self.device.width, self.device.height))
        # Paste the resized image onto the blank image
        x_offset = 0
        y_offset = (self.device.height - new_height) // 2
        final_image.paste(logo, (x_offset, y_offset))

        # Get system properties
        free_memory, ram_free, clock_freq, cpu_temp = self.get_system_properties()

        # Draw system properties on the right side
        draw = ImageDraw.Draw(final_image)
        text_x = self.device.width // 2
        text_y = 0

        draw.text((text_x, text_y), f"SD   : {free_memory:.0f}", font=self.font, fill=255)
        draw.text((text_x, text_y + 10), f"RAM : {ram_free:.1f}", font=self.font, fill=255)
        draw.text((text_x, text_y + 20), f"Freq : {clock_freq:.0f}", font=self.font, fill=255)
        draw.text((text_x, text_y + 30), f"Temp: {cpu_temp:.0f}C", font=self.font, fill=255)
        draw.text((text_x, text_y + 50), "Ready!", font=self.font, fill=255)

        # Display the final image
        self.device.display(final_image)

    def display_image(self, image_location):
        # Get the logo
        logo = Image.open(image_location).convert('RGBA')

        # Resize the image, ensuring the aspect ratio
        # Original dimensions
        orig_width, orig_height = logo.size
        # Desired dimensions
        max_width, max_height = self.device.width, self.device.height
        # Aspect ratio
        aspect_ratio = orig_width / orig_height

        # Determine new dimensions
        if (max_width / aspect_ratio) <= max_height:
            new_width = max_width
            new_height = int(max_width / aspect_ratio)
        else:
            new_height = max_height
            new_width = int(max_height * aspect_ratio)

        # Resize image maintaining aspect ratio
        logo = logo.resize((new_width, new_height))

        # Create a new blank image with the display size
        final_image = Image.new('1', (max_width, max_height))
        # Paste the resized image onto the blank image
        x_offset = (max_width - new_width) // 2
        y_offset = (max_height - new_height) // 2
        final_image.paste(logo, (x_offset, y_offset))

        self.device.display(final_image)

    def display_centered_text(self, text):

        # Load a TTF font (use a truetype font from your system)
        font = ImageFont.load_default()

        with self.get_canvas() as draw:
            # Calculate text size and position
            text_width, text_height = draw.textsize(text, font=font)
            text_x = (self.device.width - text_width) // 2
            text_y = (self.device.height - text_height) // 2

            # Draw the text
            draw.text((text_x, text_y), text, font=font, fill=255)

    def display_header_and_status(self, header, status, show_circle=False):
        final_image = Image.new('1', (self.device.width, self.device.height))
        draw = ImageDraw.Draw(final_image)

        # Draw header
        header_width, header_height = draw.textsize(header, font=self.font_large)
        header_x = (self.device.width - header_width) // 2
        header_y = 0
        draw.text((header_x, header_y), header, font=self.font_large, fill=255)

        # Draw status
        status_width, status_height = draw.textsize(status, font=self.font)
        status_x = (self.device.width - status_width) // 2
        status_y = (self.device.height - status_height) // 2
        draw.text((status_x, status_y), status, font=self.font, fill=255)

        # Optionally draw circle
        if show_circle:
            circle_x = self.device.width - 20
            circle_y = self.device.height - 20
            draw.ellipse((circle_x, circle_y, circle_x + 15, circle_y + 15), outline=255, fill=0)

        self.device.display(final_image)

    def display_progress(self, header, progress):
        final_image = Image.new('1', (self.device.width, self.device.height))
        draw = ImageDraw.Draw(final_image)

        # Draw header
        header_width, header_height = draw.textsize(header, font=self.font_large)
        header_x = (self.device.width - header_width) // 2
        header_y = 0
        draw.text((header_x, header_y), header, font=self.font_large, fill=255)

        # Draw progress bar
        bar_width = int(self.device.width * 0.8)
        bar_height = 10
        bar_x = (self.device.width - bar_width) // 2
        bar_y = (self.device.height - bar_height) // 2

        # Draw border
        draw.rectangle((bar_x, bar_y, bar_x + bar_width, bar_y + bar_height), outline=255, fill=0)
        # Draw filled part
        fill_width = int(bar_width * progress)
        draw.rectangle((bar_x, bar_y, bar_x + fill_width, bar_y + bar_height), outline=255, fill=255)

        self.device.display(final_image)

    def add_text(self, text, pos):
        with self.get_canvas() as draw:
            draw.text(pos, text, font=self.font, fill=255)


