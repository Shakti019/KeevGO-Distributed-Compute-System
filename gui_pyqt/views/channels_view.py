from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
    QPushButton, QFrame, QMessageBox, QApplication, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import pyqtSignal, Qt
from network.lan_transport import LANTransport


class ChannelsView(QWidget):
    """
    Dedicated Swarm Channels Manager View.
    """
    create_channel_clicked = pyqtSignal(str, str)  # (endpoint, transport_mode)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.channels_history = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title_lbl = QLabel("Swarm Channel Operations & Invites")
        title_lbl.setObjectName("sectionTitle")
        layout.addWidget(title_lbl)

        # Channel Creator Card
        card = QFrame()
        card.setObjectName("cardSurface")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        card_title = QLabel("Create New Swarm Channel")
        card_title.setObjectName("appTitle")
        card_layout.addWidget(card_title)

        form_row = QHBoxLayout()
        form_row.setSpacing(10)

        lbl_mode = QLabel("Transport Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["LAN (Local Wi-Fi)", "Internet (Raw TCP)"])
        form_row.addWidget(lbl_mode)
        form_row.addWidget(self.mode_combo)

        lbl_host = QLabel("Host Endpoint:")
        self.host_input = QLineEdit()
        self.host_input.setText(LANTransport.get_lan_ip())
        form_row.addWidget(lbl_host)
        form_row.addWidget(self.host_input)

        lbl_port = QLabel("Port:")
        self.port_input = QLineEdit()
        self.port_input.setText("8765")
        self.port_input.setFixedWidth(80)
        form_row.addWidget(lbl_port)
        form_row.addWidget(self.port_input)

        self.btn_create = QPushButton("Create Channel")
        self.btn_create.setObjectName("successButton")
        self.btn_create.clicked.connect(self._handle_create)
        form_row.addWidget(self.btn_create)

        card_layout.addLayout(form_row)
        layout.addWidget(card)

        # Bootstrap Invite Card
        invite_card = QFrame()
        invite_card.setObjectName("cardSurface")
        invite_layout = QVBoxLayout(invite_card)
        invite_layout.setContentsMargins(18, 16, 18, 16)
        invite_layout.setSpacing(10)

        invite_title = QLabel("Copy Friend Bootstrap Command")
        invite_title.setObjectName("appTitle")
        invite_layout.addWidget(invite_title)

        self.lbl_bootstrap = QLabel("No channel created yet.")
        self.lbl_bootstrap.setObjectName("subTitle")
        invite_layout.addWidget(self.lbl_bootstrap)

        self.btn_copy = QPushButton("Copy Bootstrap Command to Clipboard")
        self.btn_copy.setObjectName("primaryButton")
        self.btn_copy.setEnabled(False)
        self.btn_copy.clicked.connect(self._copy_bootstrap)
        invite_layout.addWidget(self.btn_copy)

        layout.addWidget(invite_card)

        # Registered Channels Table
        tbl_title = QLabel("Active & Registered Channels")
        tbl_title.setObjectName("sectionTitle")
        layout.addWidget(tbl_title)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Channel ID", "Credential Token", "Transport", "Endpoint"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.last_bootstrap_cmd = ""

    def _handle_create(self):
        host = self.host_input.text().strip()
        port = self.port_input.text().strip()
        if not host or not port:
            QMessageBox.warning(self, "Error", "Enter host and port.")
            return

        endpoint = f"{host}:{port}"
        mode = "lan" if self.mode_combo.currentIndex() == 0 else "internet"
        self.create_channel_clicked.emit(endpoint, mode)

    def on_channel_created(self, channel_id: str, credential: str, mode: str, endpoint: str, bootstrap_cmd: str):
        self.last_bootstrap_cmd = bootstrap_cmd
        self.lbl_bootstrap.setText(f"Channel {channel_id} active for {endpoint}")
        self.btn_copy.setEnabled(True)

        # Add to table
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(channel_id))
        self.table.setItem(row, 1, QTableWidgetItem(credential[:16] + "..."))
        self.table.setItem(row, 2, QTableWidgetItem(mode.upper()))
        self.table.setItem(row, 3, QTableWidgetItem(endpoint))

    def _copy_bootstrap(self):
        if self.last_bootstrap_cmd:
            QApplication.clipboard().setText(self.last_bootstrap_cmd)
            QMessageBox.information(self, "Copied", "Copied python bootstrap command to clipboard!")
