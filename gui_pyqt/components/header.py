from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit
from PyQt6.QtCore import Qt


class HeaderBar(QFrame):
    """
    Top Navigation & Status Bar in Microsoft 365 Fluent style.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("headerContainer")
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(16)

        # App Brand & Title
        self.title_label = QLabel("SHAC | Swarm Intelligence Control")
        self.title_label.setObjectName("appTitle")
        layout.addWidget(self.title_label)

        layout.addStretch()

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search nodes, channels, logs...")
        self.search_input.setFixedWidth(280)
        layout.addWidget(self.search_input)

        # Master Token Auth Badge
        self.auth_badge = QLabel("Master Admin: Verified")
        self.auth_badge.setObjectName("statusPill")
        self.auth_badge.setProperty("status", "online")
        layout.addWidget(self.auth_badge)

        # Network Server State Badge
        self.status_badge = QLabel("Server Offline")
        self.status_badge.setObjectName("statusPill")
        self.status_badge.setProperty("status", "offline")
        layout.addWidget(self.status_badge)

    def update_status(self, is_running: bool, endpoint: str = ""):
        if is_running:
            self.status_badge.setText(f"Active: {endpoint}")
            self.status_badge.setProperty("status", "online")
        else:
            self.status_badge.setText("Server Offline")
            self.status_badge.setProperty("status", "offline")
        
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
