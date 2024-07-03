from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from time import sleep
from PIL import Image, ImageDraw, ImageFont


class Display:

    def __init__(self, i2c_port=0, address=0x3C):

        # Create device
        serial = i2c(port=i2c_port, address=address)
        self.device = ssd1306(serial)
        self.font = ImageFont.load_default()

    def get_canvas(self):
        return canvas(self.device)

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

    def add_text(self, text, pos):
        with self.get_canvas() as draw:
            draw.text(pos, text, font=self.font, fill=255)


