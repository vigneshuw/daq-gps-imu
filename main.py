import time
from signal import pause
from data_handler import DataHandler


# Data Handler
data_handler = DataHandler()


if __name__ == '__main__':

    data_handler.initialize()

    pause()