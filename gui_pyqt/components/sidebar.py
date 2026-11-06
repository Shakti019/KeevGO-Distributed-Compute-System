from PyQt6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal, Qt


class Sidebar(QFrame):
    """
    Fluent Vertical Navigation Sidebar.
    """
    page_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarContainer")
        self.setFixedWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(4)

        # Category Header
        section_lbl = QLabel("NAVIGATION")
        section_lbl.setObjectName("subTitle")
        section_lbl.setContentsMargins(8, 0, 0, 6)
        layout.addWidget(section_lbl)

        # Navigation Buttons (Clean text, no emojis)
        self.buttons = []
        nav_items = [
            ("Dashboard", 0),
            ("Channels", 1),
            ("Nodes & Approvals", 2),
            ("Skills & Automation (200+)", 5),
            ("Swarm Dispatcher", 3),
            ("Audit Logs", 4),
        ]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=index: self._select_page(idx))
            layout.addWidget(btn)
            self.buttons.append((btn, index))

        layout.addStretch()

        # Bottom info badge
        bottom_lbl = QLabel("SHAC Enterprise v0.1.0")
        bottom_lbl.setObjectName("subTitle")
        bottom_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(bottom_lbl)

        # Default select index 0
        self._select_page(0)

    def _select_page(self, index: int):
        for btn, idx in self.buttons:
            is_active = (idx == index)
            btn.setChecked(is_active)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self.page_changed.emit(index)
