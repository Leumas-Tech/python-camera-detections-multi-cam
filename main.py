import sys
import cv2
import numpy as np
import multiprocessing
import json
from multiprocessing import shared_memory

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QGridLayout, QLineEdit,
                             QComboBox, QFrame, QDialog, QTextEdit, QDialogButtonBox, QMessageBox, QInputDialog, QScrollArea, QCheckBox)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

from core.workers import camera_worker
from core.camera_reader import camera_reader
from detection.object_detector import ObjectDetector # Import ObjectDetector to get class names
from utils.profile_manager import save_profile, load_profile, list_profiles
from utils.camera_manager import get_camera_sources # Import get_camera_sources
from start_screen import StartScreen

# --- Modified: DetectionConfigDialog ---
class DetectionConfigDialog(QDialog):
    def __init__(self, current_classes, model_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Detections")
        self.setGeometry(200, 200, 500, 600) # Adjusted size for checkboxes

        layout = QVBoxLayout()

        self.info_label = QLabel("Select desired detection classes. No selection means detect all.")
        layout.addWidget(self.info_label)

        # Get all available classes from the model
        try:
            temp_detector = ObjectDetector(model_name=model_name)
            self.all_classes = sorted(list(temp_detector.model.names.values()))
        except Exception as e:
            QMessageBox.warning(self, "Model Load Error", f"Could not load model {model_name} to get class names: {e}. Please ensure the model is downloaded and accessible.")
            self.all_classes = [] # Fallback to empty list

        # Scroll area for checkboxes
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.checkbox_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        self.checkboxes = []
        for cls in self.all_classes:
            checkbox = QCheckBox(cls)
            if cls in current_classes:
                checkbox.setChecked(True)
            self.checkboxes.append(checkbox)
            self.checkbox_layout.addWidget(checkbox)

        # Select All / Deselect All buttons
        select_buttons_layout = QHBoxLayout()
        select_all_button = QPushButton("Select All")
        select_all_button.clicked.connect(self.select_all_checkboxes)
        deselect_all_button = QPushButton("Deselect All")
        deselect_all_button.clicked.connect(self.deselect_all_checkboxes)
        select_buttons_layout.addWidget(select_all_button)
        select_buttons_layout.addWidget(deselect_all_button)
        layout.addLayout(select_buttons_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def select_all_checkboxes(self):
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)

    def deselect_all_checkboxes(self):
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)

    def get_selected_classes(self):
        selected = []
        for checkbox in self.checkboxes:
            if checkbox.isChecked():
                selected.append(checkbox.text())
        return selected

# --- Modified: CameraFeed to be a QFrame with fixed size ---
class CameraFeed(QFrame):
    def __init__(self, camera_id):
        super().__init__()
        self.camera_id = camera_id
        self.setFixedSize(640, 480) # Fixed size for uniform display
        self.setFrameShape(QFrame.Box)
        self.setLineWidth(2)

        self.layout = QVBoxLayout()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setText(f"Camera {camera_id} - No Feed")
        self.image_label.setStyleSheet("background-color: black; color: white;")
        self.layout.addWidget(self.image_label)
        self.setLayout(self.layout)

    def update_frame(self, frame):
        if frame is None:
            self.image_label.setText(f"Camera {self.camera_id} - Error/Disconnected")
            self.image_label.setPixmap(QPixmap()) # Clear any previous image
            return

        h, w, ch = frame.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        # Scale pixmap to fit the QLabel within the fixed QFrame size
        p = convert_to_Qt_format.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(QPixmap.fromImage(p))
        self.image_label.setText("") # Clear "No Feed" text once frame arrives

class MainWindow(QWidget):
    # Define a reasonable max frame size for shared memory (e.g., 1920x1080x3 bytes)
    MAX_FRAME_SIZE = 2560 * 1440 * 3 # Increased to support 1440p resolution

    def __init__(self, initial_configs=None):
        super().__init__()
        self.setWindowTitle("Gemini Camera Detection System")
        self.setGeometry(100, 100, 1300, 900) # Adjusted window size

        self.camera_processes = {} # Worker processes
        self.camera_queues = {} # Queues for workers to send frames to main process
        self.camera_stop_events = {} # Stop events for workers
        self.camera_feeds = {}
        self.camera_configs = {} # Store detection configurations
        self.camera_count = 0

        self.reader_processes = {} # Reader processes
        self.reader_frame_notification_queues = {} # Queues for readers to send frame info to workers
        self.reader_stop_events = {} # Stop events for readers
        self.shared_memories = {} # New: Store SharedMemory objects

        self.init_ui()
        self.populate_camera_sources()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_feeds)
        self.timer.start(30) # Update every 30 ms

        if initial_configs:
            self.load_initial_configs(initial_configs)

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Control Panel
        control_panel = QHBoxLayout()
        self.source_selector = QComboBox(self) # For available camera sources
        self.manual_source_input = QLineEdit(self) # For manual input (e.g., RTSP)
        self.manual_source_input.setPlaceholderText("Or enter camera source (e.g., 0, 1, or RTSP URL)")
        self.model_selector = QComboBox(self)
        self.model_selector.addItems(["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"])
        self.add_camera_button = QPushButton("Add Camera", self)
        self.add_camera_button.clicked.connect(self.add_camera)

        self.save_profile_button = QPushButton("Save Profile", self)
        self.save_profile_button.clicked.connect(self.save_current_profile)

        control_panel.addWidget(self.source_selector)
        control_panel.addWidget(self.manual_source_input)
        control_panel.addWidget(self.model_selector)
        control_panel.addWidget(self.add_camera_button)
        control_panel.addWidget(self.save_profile_button)

        main_layout.addLayout(control_panel)

        # Camera Grid
        self.camera_grid_layout = QGridLayout()
        main_layout.addLayout(self.camera_grid_layout)

        self.setLayout(main_layout)
        self.populate_camera_sources()

    def populate_camera_sources(self):
        self.available_camera_sources = get_camera_sources()
        if not self.available_camera_sources:
            self.source_selector.addItem("No cameras found")
            self.source_selector.setEnabled(False)
            self.add_camera_button.setEnabled(False)
        else:
            for source in self.available_camera_sources:
                self.source_selector.addItem(str(source))
            self.source_selector.setEnabled(True)
            self.add_camera_button.setEnabled(True)

    

    def load_initial_configs(self, configs):
        for config in configs:
            source = config['source']
            model_name = config['model_name']
            target_classes = config['target_classes']

            camera_id = self.camera_count
            self.camera_count += 1

            self.camera_configs[camera_id] = {
                'source': source,
                'model_name': model_name,
                'target_classes': target_classes
            }
            self._add_camera_to_gui(camera_id)
            self._start_camera_worker(camera_id)

    def _add_camera_to_gui(self, camera_id):
        feed_label = CameraFeed(camera_id)
        self.camera_feeds[camera_id] = feed_label

        # Container for feed and controls
        camera_container = QVBoxLayout()
        camera_container.addWidget(feed_label)

        config_button = QPushButton(f"Configure Camera {camera_id}")
        config_button.clicked.connect(lambda: self.open_detection_config(camera_id))
        camera_container.addWidget(config_button)

        row = (camera_id) // 2 # 2 cameras per row
        col = (camera_id) % 2
        self.camera_grid_layout.addLayout(camera_container, row, col)

    def add_camera(self):
        manual_source = self.manual_source_input.text().strip()
        selected_source = self.source_selector.currentText()
        model_name = self.model_selector.currentText()

        source = None
        if manual_source:
            source = manual_source
        elif selected_source and selected_source != "No cameras found":
            source = selected_source

        if not source:
            print("Please select or enter a camera source.")
            return

        try:
            # Try converting to int for webcam index, otherwise keep as string for URL
            source = int(source)
        except ValueError:
            pass # Keep as string if not an int

        camera_id = self.camera_count
        self.camera_count += 1

        # Initial config: detect all classes
        self.camera_configs[camera_id] = {
            'source': source,
            'model_name': model_name,
            'target_classes': [] # Empty list means detect all
        }

        self._add_camera_to_gui(camera_id)
        self._start_camera_worker(camera_id)

        # Clear manual input after adding
        self.manual_source_input.clear()

        # Remove selected item from dropdown if it was a detected camera
        if selected_source and selected_source != "No cameras found" and not manual_source:
            current_index = self.source_selector.currentIndex()
            self.source_selector.removeItem(current_index)
            if self.source_selector.count() == 0:
                self.source_selector.addItem("No more cameras available")
                self.source_selector.setEnabled(False)
                self.add_camera_button.setEnabled(False)

        print(f"Added Camera {camera_id} from source {source} with model {model_name}")

    def _start_camera_worker(self, camera_id):
        config = self.camera_configs[camera_id]
        source = config['source']
        model_name = config['model_name']
        target_classes = config['target_classes']

        # --- New: Manage CameraReader process and Shared Memory ---
        if source not in self.reader_processes or not self.reader_processes[source].is_alive():
            # Create shared memory for this source
            try:
                shm = shared_memory.SharedMemory(create=True, size=self.MAX_FRAME_SIZE)
                self.shared_memories[source] = shm
                shared_mem_name = shm.name
                shared_mem_size = shm.size
            except Exception as e:
                print(f"Error creating shared memory for source {source}: {e}")
                return

            frame_notification_queue = multiprocessing.Queue(maxsize=5) # Buffer for a few frame notifications
            reader_stop_event = multiprocessing.Event()
            reader_p = multiprocessing.Process(target=camera_reader, args=(source, shared_mem_name, shared_mem_size, frame_notification_queue, reader_stop_event))
            reader_p.daemon = True
            reader_p.start()
            self.reader_processes[source] = reader_p
            self.reader_frame_notification_queues[source] = frame_notification_queue
            self.reader_stop_events[source] = reader_stop_event
            print(f"Started CameraReader for source: {source} with shared memory: {shared_mem_name}")
        else:
            shared_mem_name = self.shared_memories[source].name
            shared_mem_size = self.shared_memories[source].size
            frame_notification_queue = self.reader_frame_notification_queues[source]

        # Clean up existing worker if any
        if camera_id in self.camera_processes and self.camera_processes[camera_id].is_alive():
            self.camera_stop_events[camera_id].set()
            self.camera_processes[camera_id].join(timeout=1)
            if self.camera_processes[camera_id].is_alive():
                self.camera_processes[camera_id].terminate()
            del self.camera_processes[camera_id]
            del self.camera_queues[camera_id]
            del self.camera_stop_events[camera_id]

        output_queue = multiprocessing.Queue(maxsize=1) # Buffer for one frame
        stop_event = multiprocessing.Event()

        # Pass shared memory details and notification queue to the worker
        p = multiprocessing.Process(target=camera_worker, args=(camera_id, shared_mem_name, shared_mem_size, frame_notification_queue, output_queue, stop_event, model_name, target_classes))
        p.daemon = True # Allow main process to exit even if workers are running
        p.start()

        self.camera_processes[camera_id] = p
        self.camera_queues[camera_id] = output_queue
        self.camera_stop_events[camera_id] = stop_event
        print(f"Started/Restarted worker for Camera {camera_id} (source {source}) with target classes: {target_classes}")

    def open_detection_config(self, camera_id):
        current_classes = self.camera_configs[camera_id]['target_classes']
        model_name = self.camera_configs[camera_id]['model_name'] # Get model name for the dialog
        dialog = DetectionConfigDialog(current_classes, model_name, self) # Pass model_name
        if dialog.exec_():
            new_classes = dialog.get_selected_classes()
            if new_classes != current_classes:
                self.camera_configs[camera_id]['target_classes'] = new_classes
                print(f"Camera {camera_id} detection classes updated to: {new_classes}")
                self._start_camera_worker(camera_id) # Restart worker with new config
            else:
                print(f"Camera {camera_id} detection classes unchanged.")

    def save_current_profile(self):
        if not self.camera_configs:
            QMessageBox.information(self, "No Cameras", "Add cameras before saving a profile.")
            return

        profile_name, ok = QInputDialog.getText(self, "Save Profile", "Enter profile name:")
        if ok and profile_name:
            # Convert camera_configs dictionary to a list for saving
            configs_to_save = []
            for cam_id in sorted(self.camera_configs.keys()):
                configs_to_save.append(self.camera_configs[cam_id])
            save_profile(profile_name, configs_to_save)
            QMessageBox.information(self, "Profile Saved", f"Profile '{profile_name}' saved successfully.")
        elif ok:
            QMessageBox.warning(self, "Invalid Name", "Profile name cannot be empty.")

    def update_feeds(self):
        for camera_id, queue in self.camera_queues.items():
            if not queue.empty():
                try:
                    frame_id, frame = queue.get_nowait()
                    if frame_id in self.camera_feeds:
                        self.camera_feeds[frame_id].update_frame(frame)
                except Exception as e:
                    print(f"Error getting frame from queue for camera {camera_id}: {e}")

    def closeEvent(self, event):
        print("Closing application. Terminating all processes...")
        # Terminate worker processes
        for camera_id, stop_event in self.camera_stop_events.items():
            stop_event.set() # Signal worker to stop
            if camera_id in self.camera_processes and self.camera_processes[camera_id].is_alive():
                self.camera_processes[camera_id].join(timeout=1) # Give it a moment to clean up
                if self.camera_processes[camera_id].is_alive():
                    self.camera_processes[camera_id].terminate() # Force terminate if not stopped
        print("All worker processes terminated.")

        # Terminate reader processes and unlink shared memory
        for source, stop_event in self.reader_stop_events.items():
            stop_event.set() # Signal reader to stop
            if source in self.reader_processes and self.reader_processes[source].is_alive():
                self.reader_processes[source].join(timeout=1) # Give it a moment to clean up
                if self.reader_processes[source].is_alive():
                    self.reader_processes[source].terminate() # Force terminate if not stopped
            # Unlink shared memory
            if source in self.shared_memories:
                self.shared_memories[source].close()
                self.shared_memories[source].unlink() # Unlink to release resources
        print("All reader processes and shared memories terminated/unlinked.")

        super().closeEvent(event)

if __name__ == "__main__":
    multiprocessing.freeze_support() # For Windows compatibility
    app = QApplication(sys.argv)

    start_screen = StartScreen()
    if start_screen.exec_(): # Show the start screen as a modal dialog
        initial_configs = start_screen.get_selected_profile_config()
        window = MainWindow(initial_configs) # Pass loaded configs to main window
        window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0) # User cancelled start screen