import threading
import time


class FileWriter(threading.Thread):
    def __init__(self, data_queue, output_file, write_interval=60):
        threading.Thread.__init__(self)
        self.data_queue = data_queue
        self.output_file = output_file
        self.running = True
        self.write_interval = write_interval

    def run(self):
        with open(self.output_file, "a") as fh:
            while self.running:
                time.sleep(self.write_interval)
                while not self.data_queue.empty():
                    fh.write(self.data_queue.get())
                fh.flush()

    def stop(self):
        self.running = False

