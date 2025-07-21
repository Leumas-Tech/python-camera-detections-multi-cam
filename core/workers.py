import cv2
from detection.object_detector import ObjectDetector
from utils.camera_utils import draw_boxes

def camera_worker(camera_id, frame_input_queue, output_queue, stop_event, model_name, target_classes):
    print(f"[CameraWorker {camera_id}] Starting with model: {model_name}, target classes: {target_classes}")
    detector = ObjectDetector(model_name=model_name)

    while not stop_event.is_set():
        if not frame_input_queue.empty():
            frame = frame_input_queue.get() # Get frame from reader process

            results = detector.detect(frame)
            annotated_frame = draw_boxes(frame, results, target_classes, detector.model.names)

            # Put the annotated frame into the queue for the main process to display
            if not output_queue.full():
                output_queue.put((camera_id, annotated_frame))
        else:
            # Small sleep to prevent busy-waiting if no frames are available
            stop_event.wait(0.001) # Wait for a very short time or until stop_event is set

    print(f"[CameraWorker {camera_id}] Exiting.")