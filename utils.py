import time


def file_writer(data_queue, output_file, write_interval=60):
    with open(output_file, "a") as fh:
        while True:
            time.sleep(write_interval)
            while not data_queue.empty():
                fh.write(data_queue.get())
            fh.flush()

