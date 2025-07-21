import sys
import cv2
import numpy as np
import multiprocessing
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QGridLayout,
                             QComboBox, QFrame, QDialog, QTextEdit, QDialogButtonBox)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

from core.workers import camera_worker

# --- New: DetectionConfigDialog ---
class DetectionConfigDialog(QDialog):
    def __init__(self, current_classes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Detections")
        self.setGeometry(200, 200, 400, 200)

        layout = QVBoxLayout()

        self.info_label = QLabel("Enter desired detection classes, separated by commas (e.g., person, car, dog). Leave empty to detect all.")
        layout.addWidget(self.info_label)

        self.class_input = QLineEdit(self)
        self.class_input.setPlaceholderText("person, car, dog")
        self.class_input.setText(", ".join(current_classes))
        layout.addWidget(self.class_input)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def get_selected_classes(self):
        text = self.class_input.text().strip()
        if not text:
            return []
        return [cls.strip() for cls in text.split(',') if cls.strip()]

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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gemini Camera Detection System")
        self.setGeometry(100, 100, 1300, 900) # Adjusted window size

        self.camera_processes = {}
        self.camera_queues = {}
        self.camera_stop_events = {}
        self.camera_feeds = {}
        self.camera_configs = {} # New: Store detection configurations
        self.camera_count = 0

        self.init_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_feeds)
        self.timer.start(30) # Update every 30 ms

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Control Panel
        control_panel = QHBoxLayout()
        self.source_input = QLineEdit(self)
        self.source_input.setPlaceholderText("Camera Source (e.g., 0, 1, or RTSP URL)")
        self.model_selector = QComboBox(self)
        self.model_selector.addItems(["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"])
        self.add_camera_button = QPushButton("Add Camera", self)
        self.add_camera_button.clicked.connect(self.add_camera)

        control_panel.addWidget(self.source_input)
        control_panel.addWidget(self.model_selector)
        control_panel.addWidget(self.add_camera_button)

        main_layout.addLayout(control_panel)

        # Camera Grid
        self.camera_grid_layout = QGridLayout()
        main_layout.addLayout(self.camera_grid_layout)

        self.setLayout(main_layout)

    def add_camera(self):
        source = self.source_input.text()
        model_name = self.model_selector.currentText()

        if not source:
            print("Please enter a camera source.")
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

        self._start_camera_worker(camera_id)

        # Add to GUI grid
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

        self.source_input.clear()
        print(f"Added Camera {camera_id} from source {source} with model {model_name}")

    def _start_camera_worker(self, camera_id):
        config = self.camera_configs[camera_id]
        source = config['source']
        model_name = config['model_name']
        target_classes = config['target_classes']

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

        p = multiprocessing.Process(target=camera_worker, args=(camera_id, source, model_name, output_queue, stop_event, target_classes))
        p.daemon = True # Allow main process to exit even if workers are running
        p.start()

        self.camera_processes[camera_id] = p
        self.camera_queues[camera_id] = output_queue
        self.camera_stop_events[camera_id] = stop_event
        print(f"Started/Restarted worker for Camera {camera_id} with target classes: {target_classes}")

    def open_detection_config(self, camera_id):
        current_classes = self.camera_configs[camera_id]['target_classes']
        dialog = DetectionConfigDialog(current_classes, self)
        if dialog.exec_():
            new_classes = dialog.get_selected_classes()
            if new_classes != current_classes:
                self.camera_configs[camera_id]['target_classes'] = new_classes
                print(f"Camera {camera_id} detection classes updated to: {new_classes}")
                self._start_camera_worker(camera_id) # Restart worker with new config
            else:
                print(f"Camera {camera_id} detection classes unchanged.")

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
        print("Closing application. Terminating camera processes...")
        for camera_id, stop_event in self.camera_stop_events.items():
            stop_event.set() # Signal worker to stop
            if camera_id in self.camera_processes and self.camera_processes[camera_id].is_alive():
                self.camera_processes[camera_id].join(timeout=1) # Give it a moment to clean up
                if self.camera_processes[camera_id].is_alive():
                    self.camera_processes[camera_id].terminate() # Force terminate if not stopped
        print("All camera processes terminated.")
        super().closeEvent(event)

if __name__ == "__main__":
    multiprocessing.freeze_support() # For Windows compatibility
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())