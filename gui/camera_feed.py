
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt

class CameraFeed(QFrame):
    def __init__(self, camera_id, size):
        super().__init__()
        self.camera_id = camera_id
        self.set_size(size)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setText(f"Camera {camera_id}\nNo Feed")
        self.image_label.setStyleSheet("background-color: #000; color: #fff; font-size: 18px;")
        self.layout.addWidget(self.image_label)
        self.setLayout(self.layout)

    def set_size(self, size):
        self.setMinimumSize(size, int(size * 0.75)) # Maintain 4:3 aspect ratio

    def update_frame(self, frame):
        if frame is None:
            self.image_label.setText(f"Camera {self.camera_id}\nError/Disconnected")
            self.image_label.setPixmap(QPixmap()) # Clear any previous image
            return

        h, w, ch = frame.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        p = convert_to_Qt_format.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(QPixmap.fromImage(p))
        self.image_label.setText("")
