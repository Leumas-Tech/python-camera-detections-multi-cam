
def get_stylesheet():
    return """
        QWidget {
            background-color: #2c3e50;
            color: #ecf0f1;
            font-family: "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif;
        }
        QMainWindow, QDialog {
            background-color: #2c3e50;
        }
        QLabel {
            font-size: 14px;
        }
        QPushButton {
            background-color: #3498db;
            color: #ecf0f1;
            border: none;
            padding: 10px 20px;
            font-size: 14px;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        QPushButton:pressed {
            background-color: #1f618d;
        }
        QLineEdit, QComboBox {
            background-color: #34495e;
            border: 1px solid #2c3e50;
            padding: 8px;
            font-size: 14px;
            border-radius: 5px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QListWidget {
            background-color: #34495e;
            border: 1px solid #2c3e50;
            padding: 5px;
            border-radius: 5px;
        }
        QFrame {
            border: 2px solid #34495e;
            border-radius: 5px;
        }
        QScrollArea {
            border: none;
        }
    """
