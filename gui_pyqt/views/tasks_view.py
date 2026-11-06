import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
    QPlainTextEdit, QPushButton, QFrame, QMessageBox
)
from PyQt6.QtCore import pyqtSignal


class TasksView(QWidget):
    """
    Consented Swarm Task Dispatcher View.
    """
    dispatch_task_clicked = pyqtSignal(str, str, dict)  # (target_node, action, params)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title_lbl = QLabel("Swarm Consented Task Dispatcher")
        title_lbl.setObjectName("sectionTitle")
        layout.addWidget(title_lbl)

        # Task Form Card
        form_card = QFrame()
        form_card.setObjectName("cardSurface")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(18, 16, 18, 16)
        form_layout.setSpacing(12)

        card_title = QLabel("Compose Audited Task Request")
        card_title.setObjectName("appTitle")
        form_layout.addWidget(card_title)

        # Target & Action Row
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        lbl_target = QLabel("Target Node:")
        self.target_input = QLineEdit()
        self.target_input.setText("all")
        self.target_input.setPlaceholderText("Node ID or 'all'")
        row1.addWidget(lbl_target)
        row1.addWidget(self.target_input)

        lbl_action = QLabel("Action Worker:")
        self.action_combo = QComboBox()
        self.action_combo.addItems(["browser.search", "file.create", "system.info"])
        row1.addWidget(lbl_action)
        row1.addWidget(self.action_combo)

        form_layout.addLayout(row1)

        # Parameters JSON Text Input
        lbl_params = QLabel("Parameters (JSON payload):")
        form_layout.addWidget(lbl_params)

        self.params_edit = QPlainTextEdit()
        self.params_edit.setPlainText('{\n  "query": "Python asyncio networking"\n}')
        self.params_edit.setFixedHeight(90)
        form_layout.addWidget(self.params_edit)

        # Dispatch Button
        self.btn_dispatch = QPushButton("Dispatch Task Request to Swarm")
        self.btn_dispatch.setObjectName("primaryButton")
        self.btn_dispatch.clicked.connect(self._handle_dispatch)
        form_layout.addWidget(self.btn_dispatch)

        layout.addWidget(form_card)

        # Audit Log View
        lbl_audit = QLabel("Swarm Task Consent & Execution Audit Trail")
        lbl_audit.setObjectName("sectionTitle")
        layout.addWidget(lbl_audit)

        self.audit_log_edit = QPlainTextEdit()
        self.audit_log_edit.setReadOnly(True)
        self.audit_log_edit.setPlaceholderText("Audited task responses and consent events will stream here...")
        layout.addWidget(self.audit_log_edit)

    def _handle_dispatch(self):
        target = self.target_input.text().strip()
        action = self.action_combo.currentText()
        raw_json = self.params_edit.toPlainText().strip()

        try:
            params = json.loads(raw_json)
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Invalid JSON", f"Parameters must be valid JSON: {e}")
            return

        self.dispatch_task_clicked.emit(target, action, params)
        self.audit_log_edit.appendPlainText(f"[DISPATCH] Sent '{action}' task to target '{target}'")

    def add_audit_record(self, record: dict):
        formatted = json.dumps(record, indent=2)
        self.audit_log_edit.appendPlainText(f"[AUDIT EVENT]\n{formatted}\n---")
