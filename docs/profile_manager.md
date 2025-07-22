# Profile Manager

This module provides functions for managing camera profiles.

## Functions

### `ensure_profiles_dir()`

Ensures that the `profiles` directory exists, creating it if necessary.

### `save_profile(profile_name, camera_configs)`

Saves a camera profile to a JSON file.

**Args:**

*   `profile_name` (str): The name of the profile to save.
*   `camera_configs` (dict): A dictionary containing the camera configurations.

### `load_profile(profile_name)`

Loads a camera profile from a JSON file.

**Args:**

*   `profile_name` (str): The name of the profile to load.

**Returns:**

*   `dict` or `None`: The loaded camera configurations, or `None` if the profile is not found.

### `list_profiles()`

Lists the available camera profiles.

**Returns:**

*   `list`: A list of profile names.

### `delete_profile(profile_name)`

Deletes a camera profile.

**Args:**

*   `profile_name` (str): The name of the profile to delete.

**Returns:**

*   `bool`: `True` if the profile was deleted, `False` otherwise.
