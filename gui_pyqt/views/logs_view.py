from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPlainTextEdit, QPushButton, QLineEdit
)
from PyQt6.QtCore import Qt


class LogsView(QWidget):
    """
    Realtime System Log Streamer & Filter View.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Title
        title_lbl = QLabel("Realtime Audit & System Console Logs")
        title_lbl.setObjectName("sectionTitle")
        layout.addWidget(title_lbl)

        # Toolbar Filters
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        lbl_filter = QLabel("Filter Level:")
        self.combo_filter = QComboBox()
        self.combo_filter.addItems(["ALL", "INFO", "SUCCESS", "WARNING", "ERROR", "CHAT"])
        toolbar.addWidget(lbl_filter)
        toolbar.addWidget(self.combo_filter)

        self.btn_clear = QPushButton("Clear Output")
        self.btn_clear.clicked.connect(self._clear_logs)
        toolbar.addWidget(self.btn_clear)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Log Text Display Pane
        self.log_edit = QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setStyleSheet("font-family: 'Segoe UI Mono', 'Consolas', monospace; font-size: 12px; background-color: #0F172A; color: #F8FAFC;")
        layout.addWidget(self.log_edit)

        # Chat Broadcast Input Bar
        chat_layout = QHBoxLayout()
        chat_layout.setSpacing(10)
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type broadcast chat message to connected swarm nodes...")
        self.chat_input.returnPressed.connect(self._on_chat_sent)
        chat_layout.addWidget(self.chat_input)

        self.btn_send_chat = QPushButton("Broadcast Chat")
        self.btn_send_chat.setObjectName("primaryButton")
        self.btn_send_chat.clicked.connect(self._on_chat_sent)
        chat_layout.addWidget(self.btn_send_chat)

        layout.addLayout(chat_layout)

    def append_log(self, level: str, message: str):
        selected_filter = self.combo_filter.currentText()
        if selected_filter != "ALL" and selected_filter != level:
            return

        prefix = f"[{level}]"
        self.log_edit.appendPlainText(f"{prefix:<10} {message}")

    def _clear_logs(self):
        self.log_edit.clear()

    def _on_chat_sent(self):
        text = self.chat_input.text().strip()
        if not text:
            return
        self.chat_input.clear()
        if hasattr(self, 'parent_app') and self.parent_app:
            self.parent_app.bridge.send_chat(text)
