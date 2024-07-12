import time
import queue


def file_writer(data_queue, output_file):
    """
    Write data from a queue to a file.

    :param data_queue: The queue handing the data
    :param output_file: Path to the file to append the data from queue
    :return: None
    """

    with open(output_file, "ab") as fh:
        buffer = bytearray()
        while True:
            try:
                encoded_data = data_queue.get(timeout=2)  # Use a timeout to prevent blocking indefinitely
                if encoded_data is None:
                    break
                buffer.extend(encoded_data)
                if len(buffer) > 4096:  # Write to file when buffer exceeds 4KB
                    fh.write(buffer)
                    fh.flush()
                    buffer.clear()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error writing to file: {e}")
                break
        if buffer:
            fh.write(buffer)
            fh.flush()
