import json
import os

PROFILES_DIR = "profiles"

def ensure_profiles_dir():
    if not os.path.exists(PROFILES_DIR):
        os.makedirs(PROFILES_DIR)

def save_profile(profile_name, camera_configs):
    ensure_profiles_dir()
    file_path = os.path.join(PROFILES_DIR, f"{profile_name}.json")
    with open(file_path, 'w') as f:
        json.dump(camera_configs, f, indent=4)
    print(f"Profile '{profile_name}' saved to {file_path}")

def load_profile(profile_name):
    ensure_profiles_dir()
    file_path = os.path.join(PROFILES_DIR, f"{profile_name}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            camera_configs = json.load(f)
        print(f"Profile '{profile_name}' loaded from {file_path}")
        return camera_configs
    else:
        print(f"Profile '{profile_name}' not found at {file_path}")
        return None

def list_profiles():
    ensure_profiles_dir()
    profiles = []
    for filename in os.listdir(PROFILES_DIR):
        if filename.endswith(".json"):
            profiles.append(os.path.splitext(filename)[0])
    return profiles