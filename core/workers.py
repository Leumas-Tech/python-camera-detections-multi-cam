import cv2
from detection.object_detector import ObjectDetector
from utils.camera_utils import draw_boxes

def camera_worker(camera_id, source, model_name, output_queue, stop_event, target_classes):
    print(f"[CameraWorker {camera_id}] Starting for source: {source} with model: {model_name}, target classes: {target_classes}")
    detector = ObjectDetector(model_name=model_name)
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[CameraWorker {camera_id}] Error: Could not open video source {source}")
        output_queue.put((camera_id, None)) # Signal error to main process
        return

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            print(f"[CameraWorker {camera_id}] End of stream or error for source {source}")
            break

        results = detector.detect(frame)

        # Filter results based on target_classes
        filtered_results = []
        if target_classes:
            for r in results:
                # Get class names from the model for filtering
                class_names = detector.model.names
                # Create a list of indices for the target classes
                target_class_indices = [k for k, v in class_names.items() if v in target_classes]

                # Filter boxes based on target_class_indices
                if r.boxes is not None:
                    # Ensure r.boxes.cls is a tensor before converting to list
                    if hasattr(r.boxes.cls, 'tolist'):
                        filtered_boxes_indices = [i for i, cls_idx in enumerate(r.boxes.cls.tolist()) if cls_idx in target_class_indices]
                    else:
                        filtered_boxes_indices = [] # No boxes or unexpected format

                    if filtered_boxes_indices:
                        # Create a new result object with only the filtered boxes
                        # This is a simplified approach; a more robust solution might involve deep copying and modifying the result object
                        # For now, we'll just pass the original results and let draw_boxes handle it if it can.
                        # A better way would be to create a new Results object with filtered boxes.
                        # For simplicity in this MVP, we'll rely on draw_boxes to only draw what's relevant.
                        # However, to truly filter, we need to modify the results object itself.
                        # Let's create a dummy result object for now, and improve if needed.
                        # This part needs careful handling as ultralytics results objects are complex.
                        # For now, let's pass the original results and filter within draw_boxes or rely on the model's internal filtering if available.
                        # A more direct way is to modify the boxes attribute of the result object.
                        
                        # Let's try to filter the boxes directly within the result object
                        # This assumes r.boxes is a Boxes object from ultralytics
                        if hasattr(r, 'boxes') and r.boxes is not None:
                            # Get the original boxes data
                            original_boxes_data = r.boxes.data
                            # Filter the data based on class indices
                            filtered_data = [box for box in original_boxes_data if int(box[5]) in target_class_indices] # box[5] is class index
                            
                            # Create a new Boxes object with filtered data
                            # This requires knowing how to construct a Boxes object, which might be complex.
                            # A simpler approach for MVP: pass the target_classes to draw_boxes and let it filter.
                            # Let's revert to passing target_classes to draw_boxes for simplicity in MVP.
                            filtered_results.append(r) # Keep original result for now, filtering will happen in draw_boxes
                else:
                    filtered_results.append(r) # If no boxes, keep the result (e.g., for segmentation masks if any)
        else:
            filtered_results = results # If no target classes, keep all results

        annotated_frame = draw_boxes(frame, filtered_results, target_classes, detector.model.names)

        # Put the annotated frame into the queue for the main process to display
        output_queue.put((camera_id, annotated_frame))

    cap.release()
    print(f"[CameraWorker {camera_id}] Exiting.")