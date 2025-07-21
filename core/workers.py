import cv2
import numpy as np
from multiprocessing import shared_memory

from detection.object_detector import ObjectDetector
from utils.camera_utils import draw_boxes

def camera_worker(camera_id, shared_mem_name, shared_mem_size, frame_notification_queue, output_queue, stop_event, model_name, target_classes):
    print(f"[CameraWorker {camera_id}] Starting with model: {model_name}, target classes: {target_classes}")
    detector = ObjectDetector(model_name=model_name)

    # Attach to the shared memory block
    try:
        shm = shared_memory.SharedMemory(name=shared_mem_name)
        shared_buffer = shm.buf
    except Exception as e:
        print(f"[CameraWorker {camera_id}] Error attaching to shared memory: {e}")
        stop_event.set()
        return

    while not stop_event.is_set():
        if not frame_notification_queue.empty():
            frame_shape, frame_dtype = frame_notification_queue.get() # Get frame info from reader process

            # Reconstruct the frame from shared memory
            frame = np.ndarray(frame_shape, dtype=frame_dtype, buffer=shared_buffer)

            results = detector.detect(frame)
            annotated_frame = draw_boxes(frame, results, target_classes, detector.model.names)

            # Put the annotated frame into the queue for the main process to display
            if not output_queue.full():
                output_queue.put((camera_id, annotated_frame))
        else:
            # Small sleep to prevent busy-waiting if no frames are available
            stop_event.wait(0.001) # Wait for a very short time or until stop_event is set

    shm.close() # Close the shared memory connection
    print(f"[CameraWorker {camera_id}] Exiting.")