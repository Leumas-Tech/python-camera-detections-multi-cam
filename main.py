
import sys
import multiprocessing

from PyQt5.QtWidgets import QApplication

from gui.start_screen import StartScreen
from gui.main_window import MainWindow

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
