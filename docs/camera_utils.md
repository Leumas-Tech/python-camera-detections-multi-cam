# Camera Utils

This module provides utility functions for working with cameras.

## Functions

### `draw_boxes(frame, results, target_classes=None, class_names=None)`

Draws bounding boxes on a frame based on the detection results.

**Args:**

*   `frame` (numpy.ndarray): The image frame to draw on.
*   `results` (list): A list of detection results from the object detector.
*   `target_classes` (list, optional): A list of class names to draw. If `None`, all classes are drawn. Defaults to `None`.
*   `class_names` (list, optional): A list of all possible class names. Defaults to `None`.

**Returns:**

*   `numpy.ndarray`: The frame with bounding boxes drawn.
