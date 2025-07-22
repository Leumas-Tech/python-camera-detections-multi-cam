import cv2
import numpy as np
from multiprocessing import shared_memory

from detection.object_detector import ObjectDetector
from utils.camera_utils import draw_boxes

from utils.camera_utils import draw_boxes, draw_faces

def camera_worker(camera_id, shared_mem_name, shared_mem_size, frame_notification_queue, output_queue, stop_event, model_name, target_classes, enable_face_detection):
    print(f"[CameraWorker {camera_id}] Starting with model: {model_name}, target classes: {target_classes}")
    detector = ObjectDetector(model_name=model_name)

    face_cascade = None
    if enable_face_detection:
        # Load the Haar cascade for face detection
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        if face_cascade.empty():
            print(f"[CameraWorker {camera_id}] WARNING: Could not load face cascade classifier.")
        else:
            print(f"[CameraWorker {camera_id}] Face Detection Enabled.")

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
            annotated_frame = frame.copy() # Initialize annotated_frame with a copy of the original frame

            # Object Detection
            results = [] # Initialize results to an empty list
            try:
                results = detector.detect(frame)
            except Exception as e:
                print(f"[CameraWorker {camera_id}] Error during object detection: {e}")
                # results remains an empty list

            annotated_frame = draw_boxes(annotated_frame, results, target_classes, detector.model.names)

            # Face Detection
            if enable_face_detection and face_cascade:
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray_frame, 1.1, 4)
                annotated_frame = draw_faces(annotated_frame, faces)

            # Put the annotated frame into the queue for the main process to display
            try:
                output_queue.put_nowait((camera_id, annotated_frame))
            except _queue.Full:
                # If the queue is full, the main process is not consuming fast enough.
                # We can drop the frame to avoid blocking the worker.
                pass
        else:
            # Small sleep to prevent busy-waiting if no frames are available
            stop_event.wait(0.001) # Wait for a very short time or until stop_event is set

    shm.close() # Close the shared memory connection
    print(f"[CameraWorker {camera_id}] Exiting.")