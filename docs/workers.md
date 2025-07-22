# Workers

This module defines the `camera_worker` function, which is responsible for processing frames from a camera source in a separate process.

## Functions

### `camera_worker(camera_id, shared_mem_name, shared_mem_size, frame_notification_queue, output_queue, stop_event, model_name, target_classes)`

Processes frames from a camera source, performs object detection, and puts the annotated frames into an output queue.

**Args:**

*   `camera_id` (int): The ID of the camera.
*   `shared_mem_name` (str): The name of the shared memory block.
*   `shared_mem_size` (int): The size of the shared memory block.
*   `frame_notification_queue` (multiprocessing.Queue): A queue to receive notifications about new frames.
*   `output_queue` (multiprocessing.Queue): A queue to send annotated frames to the main process.
*   `stop_event` (multiprocessing.Event): An event to signal the process to stop.
*   `model_name` (str): The name of the YOLOv8 model to use.
*   `target_classes` (list): A list of target classes to detect.
