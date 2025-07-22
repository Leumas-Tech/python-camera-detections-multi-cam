# Camera Reader

This module defines the `camera_reader` function, which is responsible for reading frames from a camera source in a separate process.

## Functions

### `camera_reader(source, shared_mem_name, shared_mem_size, frame_notification_queue, stop_event)`

Reads frames from a camera source and writes them to shared memory.

**Args:**

*   `source` (int or str): The camera source (index or URL).
*   `shared_mem_name` (str): The name of the shared memory block.
*   `shared_mem_size` (int): The size of the shared memory block.
*   `frame_notification_queue` (multiprocessing.Queue): A queue to notify worker processes about new frames.
*   `stop_event` (multiprocessing.Event): An event to signal the process to stop.
