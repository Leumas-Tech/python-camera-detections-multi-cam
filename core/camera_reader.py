import cv2
import time
import numpy as np
from multiprocessing import shared_memory

def camera_reader(source, shared_mem_name, shared_mem_size, frame_notification_queue, stop_event):
    print(f"[CameraReader {source}] Starting reader for source: {source}")
    # --- Modified: Use DSHOW backend on Windows for better compatibility ---
    import platform
    if platform.system() == "Windows" and isinstance(source, int):
        cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(source)
    # --- End Modification ---

    if not cap.isOpened():
        print(f"[CameraReader {source}] Error: Could not open video source {source}")
        stop_event.set() # Signal error
        return
    print(f"[CameraReader {source}] Camera opened successfully.")

    # Attach to the shared memory block
    try:
        shm = shared_memory.SharedMemory(name=shared_mem_name)
        shared_buffer = shm.buf
        print(f"[CameraReader {source}] Attached to shared memory: {shared_mem_name}")
    except Exception as e:
        print(f"[CameraReader {source}] Error attaching to shared memory: {e}")
        stop_event.set()
        return

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            print(f"[CameraReader {source}] End of stream or error for source {source}")
            break

        # Ensure the frame is C-contiguous for consistent tobytes() behavior
        if not frame.flags['C_CONTIGUOUS']:
            frame = np.ascontiguousarray(frame)

        # Ensure frame fits in shared memory
        frame_bytes = frame.tobytes()
        if len(frame_bytes) > shared_mem_size:
            print(f"[CameraReader {source}] Warning: Frame too large ({len(frame_bytes)} bytes) for shared memory ({shared_mem_size} bytes). Skipping frame.")
            continue

        # Write frame to shared memory
        shared_buffer[:len(frame_bytes)] = frame_bytes

        # Put frame shape and dtype into queue for workers to reconstruct
        frame_info = (frame.shape, frame.dtype)
        if not frame_notification_queue.full():
            frame_notification_queue.put(frame_info)
            # print(f"[CameraReader {source}] Put frame info to queue. Shape: {frame.shape}, Dtype: {frame.dtype}")
        else:
            print(f"[CameraReader {source}] Frame notification queue full, dropping frame notification.")

        time.sleep(0.001) # Small delay to prevent busy-waiting

    cap.release()
    shm.close() # Close the shared memory connection
    print(f"[CameraReader {source}] Exiting.")