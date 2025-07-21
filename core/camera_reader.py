import cv2
import time

def camera_reader(source, frame_queue, stop_event):
    print(f"[CameraReader {source}] Starting reader for source: {source}")
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[CameraReader {source}] Error: Could not open video source {source}")
        stop_event.set() # Signal error
        return

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            print(f"[CameraReader {source}] End of stream or error for source {source}")
            break

        # Put frame into queue. If queue is full, it means workers are slow,
        # so we drop the oldest frame to keep up with live stream.
        if not frame_queue.full():
            frame_queue.put(frame)
        else:
            # Optionally, log that a frame was dropped
            # print(f"[CameraReader {source}] Frame queue full, dropping frame.")
            pass

        time.sleep(0.01) # Small delay to prevent busy-waiting and allow other processes to run

    cap.release()
    print(f"[CameraReader {source}] Exiting.")