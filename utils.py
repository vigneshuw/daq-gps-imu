import time


def file_writer(data_queue, output_file, write_interval=60):
    with open(output_file, "a") as fh:
        while True:
            time.sleep(write_interval)
            batch = []
            while not data_queue.empty():
                batch.append(data_queue.get())
            if batch:
                fh.write("".join(batch))
                fh.flush()
