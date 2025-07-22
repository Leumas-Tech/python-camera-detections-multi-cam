# Camera Manager

This module provides functions for managing camera sources.

## Functions

### `get_camera_sources()`

Discovers available camera sources by attempting to open them. It iterates through camera indices and returns a list of indices corresponding to available cameras.

**Returns:**

*   `list`: A list of integers representing the available camera indices.
