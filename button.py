from gpiozero import Button
import time


class ButtonHandler:
    """
    Responsible for handling button and release. Suitable for push buttons
    """

    def __init__(self, pin, press_duration, on_button_held_callback=None, on_button_released_callback=None,
                 release_required=True):
        self.button = Button(pin)
        self.button_press_time = 0
        self.press_duration = press_duration
        self.button_held = False
        self.release_required = release_required

        # Callbacks
        self.on_button_held_callback = on_button_held_callback
        self.on_button_released_callback = on_button_released_callback

        # Attach to press and release events
        self.button.when_pressed = self.button_pressed
        self.button.when_released = self.button_released

    def button_pressed(self):
        """
        Callback when the button has been pressed

        :return: None
        """

        self.button_press_time = time.monotonic()

    def button_released(self):
        """
        Callback when the button has been released

        :return: None
        """

        press_duration = time.monotonic() - self.button_press_time
        if not self.button_held and press_duration > self.press_duration:
            self.button_held = True
            self.on_button_held()

            # If release not required
            if not self.release_required:
                self.button_held = False

        elif self.button_held and press_duration > self.press_duration:
            self.button_held = False
            self.on_button_released()

    def on_button_held(self):
        """
        Called when the button push is registered to be valid

        :return: None
        """

        if self.on_button_held_callback:
            self.on_button_held_callback()

    def on_button_released(self):
        """
        Called when the button release is registered to be valid

        :return: None
        """

        if self.on_button_released_callback:
            self.on_button_released_callback()

    def deactivate(self):
        """
        Deactivate press and release

        :return: None
        """

        self.button.when_pressed = None
        self.button.when_released = None

    def reactivate(self):
        """
        Reactivate press and release

        :return: None
        """

        self.button.when_pressed = self.button_pressed
        self.button.when_released = self.button_released
