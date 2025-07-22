# Object Detector

This module provides a simple interface for performing object detection using YOLOv8.

## Classes

### `ObjectDetector`

An object detector that uses the YOLOv8 model.

**Args:**

*   `model_name` (str, optional): The name of the YOLOv8 model to use. Defaults to `"yolov8n.pt"`.

#### Methods

##### `detect(frame)`

Performs object detection on a single frame.

**Args:**

*   `frame` (numpy.ndarray): The image frame to process.

**Returns:**

*   `list`: A list of detection results.
