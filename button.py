from gpiozero import Button
import time


class ButtonHandler:

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
        self.button_press_time = time.time()

    def button_released(self):
        press_duration = time.time() - self.button_press_time
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
        if self.on_button_held_callback:
            self.on_button_held_callback()

    def on_button_released(self):
        if self.on_button_released_callback:
            self.on_button_released_callback()

    def deactivate(self):
        self.button.when_pressed = None
        self.button.when_released = None

    def reactivate(self):
        self.button.when_pressed = self.button_pressed
        self.button.when_released = self.button_released
