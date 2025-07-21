import cv2

def get_camera_sources():
    # Attempt to open cameras at indices 0, 1, and 2
    # In a real application, this would load from a config file or discover cameras
    # For now, we'll try common indices.
    # --- Modified: Use DSHOW backend on Windows for better compatibility ---
    import platform
    available_cameras = []
    for i in range(10): # Try indices from 0 to 9 to discover more cameras
        if platform.system() == "Windows":
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available_cameras.append(i)
            cap.release() # Release the camera immediately
    return available_cameras