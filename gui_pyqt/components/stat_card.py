from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor


class StatCard(QFrame):
    """
    Elevated Microsoft 365 style KPI metric card widget.
    """
    def __init__(self, title: str, initial_value: str = "0", parent=None):
        super().__init__(parent)
        self.setObjectName("cardSurface")
        self.setMinimumHeight(95)

        # Subtle Drop Shadow Effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(15, 23, 42, 18))  # Slate dark shadow alpha
        shadow.setYOffset(3)
        shadow.setXOffset(0)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("statLabel")
        layout.addWidget(self.title_label)

        self.value_label = QLabel(initial_value)
        self.value_label.setObjectName("statValue")
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)
