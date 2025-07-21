import sys
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                             QPushButton, QListWidget, QLineEdit, QLabel, QMessageBox)
from PyQt5.QtCore import Qt

from utils.profile_manager import list_profiles, load_profile

class StartScreen(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gemini Camera Detection System - Start")
        self.setGeometry(300, 300, 400, 300)
        self.setModal(True) # Make it a modal dialog

        self.selected_profile_config = None

        self.init_ui()
        self.load_profile_list()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # New Session
        new_session_layout = QHBoxLayout()
        new_session_layout.addWidget(QLabel("Start New Session:"))
        self.new_session_button = QPushButton("New Session")
        self.new_session_button.clicked.connect(self.start_new_session)
        new_session_layout.addWidget(self.new_session_button)
        main_layout.addLayout(new_session_layout)

        main_layout.addStretch(1)

        # Load Profile
        load_profile_label = QLabel("Load Existing Profile:")
        main_layout.addWidget(load_profile_label)

        self.profile_list_widget = QListWidget()
        self.profile_list_widget.itemDoubleClicked.connect(self.load_selected_profile)
        main_layout.addWidget(self.profile_list_widget)

        load_button_layout = QHBoxLayout()
        self.load_profile_button = QPushButton("Load Profile")
        self.load_profile_button.clicked.connect(self.load_selected_profile)
        load_button_layout.addWidget(self.load_profile_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_profile_list)
        load_button_layout.addWidget(self.refresh_button)

        main_layout.addLayout(load_button_layout)

        self.setLayout(main_layout)

    def load_profile_list(self):
        self.profile_list_widget.clear()
        profiles = list_profiles()
        if not profiles:
            self.profile_list_widget.addItem("No profiles found.")
            self.profile_list_widget.setEnabled(False)
            self.load_profile_button.setEnabled(False)
        else:
            self.profile_list_widget.setEnabled(True)
            self.load_profile_button.setEnabled(True)
            for profile in profiles:
                self.profile_list_widget.addItem(profile)

    def start_new_session(self):
        self.selected_profile_config = [] # Empty list for new session
        self.accept()

    def load_selected_profile(self):
        selected_items = self.profile_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Profile Selected", "Please select a profile to load.")
            return

        profile_name = selected_items[0].text()
        config = load_profile(profile_name)
        if config is not None:
            self.selected_profile_config = config
            self.accept()
        else:
            QMessageBox.critical(self, "Error Loading Profile", f"Could not load profile: {profile_name}")

    def get_selected_profile_config(self):
        return self.selected_profile_config

if __name__ == "__main__":
    app = QApplication(sys.argv)
    start_screen = StartScreen()
    if start_screen.exec_():
        config = start_screen.get_selected_profile_config()
        if config is not None:
            print("Loaded config:", config)
        else:
            print("Starting new session.")
    else:
        print("Start screen cancelled.")
    sys.exit(0)