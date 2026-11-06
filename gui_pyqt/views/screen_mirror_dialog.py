import base64
import time
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage


class ScreenMirrorWindow(QDialog):
    """
    Dedicated Remote Visual Screen Mirroring Window for real-time live device screen streaming.
    """
    def __init__(self, node_id: str, address: str, bridge, parent=None):
        super().__init__(parent)
        self.node_id = node_id
        self.address = address
        self.bridge = bridge
        self.frame_count = 0
        self.last_frame_time = time.time()
        self.current_pixmap = None
        self.is_mirroring = False

        self.setWindowTitle(f"Realtime Visual Screen Mirror // Node {node_id} ({address})")
        self.resize(960, 600)
        self.setMinimumSize(640, 400)

        self.setStyleSheet("""
            QDialog {
                background-color: #090D16;
                color: #00FF9D;
            }
            QLabel {
                color: #00F0FF;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-weight: bold;
                font-size: 13px;
            }
            QFrame#canvasBorder {
                background-color: #050810;
                border: 2px solid #1E293B;
                border-radius: 8px;
            }
            QComboBox {
                background-color: #0F172A;
                color: #FFFFFF;
                border: 1px solid #00F0FF;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QPushButton {
                background-color: #00F0FF;
                color: #090D16;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #00FF9D;
            }
            QPushButton#btnStop {
                background-color: #EF4444;
                color: #FFFFFF;
            }
            QPushButton#btnStop:hover {
                background-color: #DC2626;
            }
            QPushButton#btnStart {
                background-color: #10B981;
                color: #FFFFFF;
            }
            QPushButton#btnStart:hover {
                background-color: #059669;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Controls Bar
        header = QHBoxLayout()
        header.setSpacing(10)

        self.lbl_title = QLabel(f"📺 LIVE REALTIME SCREEN MIRROR // Node {node_id} ({address})")
        header.addWidget(self.lbl_title)

        header.addStretch()

        header.addWidget(QLabel("Refresh Stream Rate:"))
        self.fps_combo = QComboBox()
        self.fps_combo.addItem("1 Frame/sec (1000ms)", 1000)
        self.fps_combo.addItem("2 Frames/sec (500ms)", 500)
        self.fps_combo.addItem("5 Frames/sec (200ms)", 200)
        self.fps_combo.currentIndexChanged.connect(self._update_timer_interval)
        header.addWidget(self.fps_combo)

        self.btn_toggle = QPushButton("▶ Start Screen Mirroring")
        self.btn_toggle.setObjectName("btnStart")
        self.btn_toggle.clicked.connect(self._toggle_mirroring)
        header.addWidget(self.btn_toggle)

        layout.addLayout(header)

        # Main Screen Display Canvas Frame
        self.canvas_frame = QFrame()
        self.canvas_frame.setObjectName("canvasBorder")
        canvas_layout = QVBoxLayout(self.canvas_frame)
        canvas_layout.setContentsMargins(8, 8, 8, 8)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setText("Click '▶ Start Screen Mirroring' for live single-consent visual stream...")
        self.image_label.setStyleSheet("font-size: 14px; color: #94A3B8;")
        canvas_layout.addWidget(self.image_label)

        layout.addWidget(self.canvas_frame, stretch=1)

        # Status Footer Bar
        footer = QHBoxLayout()
        self.lbl_stats = QLabel("Status: Standby | Frames: 0 | Latency: 0ms")
        footer.addWidget(self.lbl_stats)
        layout.addLayout(footer)

        # Timer for requesting periodic frames
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(1000)
        self.poll_timer.timeout.connect(self._request_frame)

        # Connect Bridge Signal for incoming task responses
        if self.bridge:
            self.bridge.task_response_received.connect(self.on_task_response)

    def _toggle_mirroring(self):
        if not self.is_mirroring:
            self.is_mirroring = True
            self.btn_toggle.setText("⏹ Stop Mirroring")
            self.btn_toggle.setObjectName("btnStop")
            self.btn_toggle.style().unpolish(self.btn_toggle)
            self.btn_toggle.style().polish(self.btn_toggle)
            self.image_label.setText("Requesting visual screen mirror stream...")
            self.poll_timer.start()
            self._request_frame()
        else:
            self.is_mirroring = False
            self.btn_toggle.setText("▶ Start Screen Mirroring")
            self.btn_toggle.setObjectName("btnStart")
            self.btn_toggle.style().unpolish(self.btn_toggle)
            self.btn_toggle.style().polish(self.btn_toggle)
            self.poll_timer.stop()
            if self.bridge:
                self.bridge.send_task(self.node_id, "screen.stop", {})
            self.lbl_stats.setText(f"Status: Stopped | Total Frames Streamed: {self.frame_count}")

    def _update_timer_interval(self, index: int):
        interval = self.fps_combo.itemData(index)
        if interval:
            self.poll_timer.setInterval(interval)

    def _request_frame(self):
        if not self.is_mirroring or not self.bridge:
            return
        self.bridge.send_task(self.node_id, "screen.frame", {})

    def on_task_response(self, resp: dict):
        if not self.is_mirroring:
            return
        
        nid = resp.get("node_id", "")
        action = resp.get("action", "")
        if nid != self.node_id or action not in ("screen.frame", "screen.mirror"):
            return

        b64_data = resp.get("stdout", "").strip()
        if not b64_data:
            return

        try:
            image_bytes = base64.b64decode(b64_data)
            qimg = QImage()
            if qimg.loadFromData(image_bytes):
                pixmap = QPixmap.fromImage(qimg)
                self.current_pixmap = pixmap
                self.frame_count += 1
                
                # Render scaled pixmap maintaining aspect ratio
                scaled = pixmap.scaled(
                    self.image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(scaled)

                now = time.time()
                latency = int((now - self.last_frame_time) * 1000)
                self.last_frame_time = now
                self.lbl_stats.setText(
                    f"Status: STREAMING LIVE | Frames: {self.frame_count} | "
                    f"Resolution: {pixmap.width()}x{pixmap.height()} | Latency: {latency}ms"
                )
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_pixmap and not self.current_pixmap.isNull():
            scaled = self.current_pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)

    def closeEvent(self, event):
        self.is_mirroring = False
        self.poll_timer.stop()
        if self.bridge:
            self.bridge.send_task(self.node_id, "screen.stop", {})
        event.accept()
