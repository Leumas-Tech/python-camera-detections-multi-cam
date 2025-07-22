
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QDialogButtonBox, QMessageBox, QScrollArea, QCheckBox, QWidget)
from detection.object_detector import ObjectDetector
from gui.stylesheet import get_stylesheet

class DetectionConfigDialog(QDialog):
    def __init__(self, current_config, model_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Detections")
        self.setGeometry(200, 200, 500, 600) # Adjusted size for checkboxes
        self.setStyleSheet(get_stylesheet())

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.info_label = QLabel("Select desired detection classes. No selection means detect all.")
        layout.addWidget(self.info_label)

        # New: Face Detection Checkbox
        self.face_detection_checkbox = QCheckBox("Enable Face Detection")
        self.face_detection_checkbox.setChecked(current_config.get('enable_face_detection', False))
        layout.addWidget(self.face_detection_checkbox)

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
        current_object_classes = current_config.get('target_classes', [])
        for cls in self.all_classes:
            checkbox = QCheckBox(cls)
            if cls in current_object_classes:
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

    def get_selected_config(self):
        selected_classes = []
        for checkbox in self.checkboxes:
            if checkbox.isChecked():
                selected_classes.append(checkbox.text())
        return {
            'target_classes': selected_classes,
            'enable_face_detection': self.face_detection_checkbox.isChecked()
        }
