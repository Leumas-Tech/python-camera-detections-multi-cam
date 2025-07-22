
import multiprocessing
from multiprocessing import shared_memory

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit,
                             QComboBox, QGridLayout, QMessageBox, QInputDialog, QLabel)
from PyQt5.QtCore import QTimer, Qt
from gui.stylesheet import get_stylesheet

from core.workers import camera_worker
from core.camera_reader import camera_reader
from utils.profile_manager import save_profile
from utils.camera_manager import get_camera_sources
from gui.camera_feed import CameraFeed
from gui.detection_config_dialog import DetectionConfigDialog

class MainWindow(QWidget):
    # Define a reasonable max frame size for shared memory (e.g., 1920x1080x3 bytes)
    MAX_FRAME_SIZE = 2560 * 1440 * 3 # Increased to support 1440p resolution

    def __init__(self, initial_configs=None):
        super().__init__()
        self.setWindowTitle("Gemini Camera Detection System")
        self.setGeometry(100, 100, 1300, 900) # Adjusted window size
        self.setStyleSheet(get_stylesheet())

        self.camera_processes = {} # Worker processes
        self.camera_queues = {} # Queues for workers to send frames to main process
        self.camera_stop_events = {} # Stop events for workers
        self.camera_feeds = {}
        self.camera_configs = {} # Store detection configurations
        self.camera_count = 0
        self.current_page = 0
        self.cameras_per_page = 4 # Default value
        self.camera_size = 640 # Default value

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
        self.update_grid() # Initial grid update after all setup

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Control Panel
        control_panel = QHBoxLayout()
        control_panel.setSpacing(10)
        
        self.source_selector = QComboBox(self) # For available camera sources
        self.source_selector.setPlaceholderText("Select a camera")
        self.manual_source_input = QLineEdit(self) # For manual input (e.g., RTSP)
        self.manual_source_input.setPlaceholderText("Or enter camera source (e.g., 0, 1, or RTSP URL)")
        self.model_selector = QComboBox(self)
        self.model_selector.addItems(["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"])
        self.add_camera_button = QPushButton("Add Camera", self)
        self.add_camera_button.clicked.connect(self.add_camera)

        self.save_profile_button = QPushButton("Save Profile", self)
        self.save_profile_button.clicked.connect(self.save_current_profile)

        control_panel.addWidget(self.source_selector, 1)
        control_panel.addWidget(self.manual_source_input, 2)
        control_panel.addWidget(self.model_selector, 1)
        control_panel.addWidget(self.add_camera_button)
        control_panel.addWidget(self.save_profile_button)

        main_layout.addLayout(control_panel)

        # Camera Grid
        self.camera_grid_layout = QGridLayout()
        self.camera_grid_layout.setSpacing(15)
        main_layout.addLayout(self.camera_grid_layout)

        # ←–––––––––––––––––––––––––––––––––––––––––––––
        # Pagination controls
        pagination = QHBoxLayout()
        pagination.setSpacing(10)

        self.prev_button = QPushButton("Previous", self)
        self.prev_button.clicked.connect(self.prev_page)
        pagination.addWidget(self.prev_button)

        self.page_label = QLabel("", self)
        self.page_label.setAlignment(Qt.AlignCenter)
        pagination.addWidget(self.page_label, 1)  # stretch of 1 so it expands

        self.next_button = QPushButton("Next", self)
        self.next_button.clicked.connect(self.next_page)
        pagination.addWidget(self.next_button)

        main_layout.addLayout(pagination)
        # ←–––––––––––––––––––––––––––––––––––––––––––––

        main_layout.addStretch(1)

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
        self.update_grid() # Update grid after loading all initial configs

    def update_grid(self):
        for i in reversed(range(self.camera_grid_layout.count())):
            self.camera_grid_layout.itemAt(i).widget().setParent(None)

        start_index = self.current_page * self.cameras_per_page
        end_index = start_index + self.cameras_per_page
        visible_cameras = list(self.camera_feeds.keys())[start_index:end_index]

        cols = int(self.cameras_per_page ** 0.5)
        for i, camera_id in enumerate(visible_cameras):
            row = i // cols
            col = i % cols
            self.camera_grid_layout.addWidget(self.camera_feeds[camera_id], row, col)

        self.update_page_label()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_grid()

    def next_page(self):
        if (self.current_page + 1) * self.cameras_per_page < len(self.camera_feeds):
            self.current_page += 1
            self.update_grid()

    def update_page_label(self):
        total_pages = (len(self.camera_feeds) + self.cameras_per_page - 1) // self.cameras_per_page
        self.page_label.setText(f"Page {self.current_page + 1} of {total_pages}")

    def update_cameras_per_page(self, value):
        self.cameras_per_page = int(value)
        self.current_page = 0
        self.update_grid()

    def update_camera_size(self, value):
        self.camera_size = value
        for feed in self.camera_feeds.values():
            feed.set_size(self.camera_size)

    def _add_camera_to_gui(self, camera_id):
        feed_label = CameraFeed(camera_id, self.camera_size)
        self.camera_feeds[camera_id] = feed_label
        self.update_grid()

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
