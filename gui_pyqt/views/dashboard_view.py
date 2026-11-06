from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, 
    QLineEdit, QFrame, QMessageBox, QApplication, QPlainTextEdit
)
from PyQt6.QtCore import pyqtSignal, Qt
from gui_pyqt.components.stat_card import StatCard
from gui_pyqt.components.node_table import NodeTableWidget
from network.lan_transport import LANTransport


class DashboardView(QWidget):
    """
    Main Overview Dashboard in Microsoft 365 White Enterprise Style.
    """
    start_server_clicked = pyqtSignal(str, int, str)  # (host, port, mode)
    stop_server_clicked = pyqtSignal()
    create_channel_clicked = pyqtSignal(str)          # (endpoint)
    approve_node_clicked = pyqtSignal(str)
    reject_node_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bootstrap_payload = ""

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 1. Page Header Title
        title_lbl = QLabel("System Dashboard & Control Plane")
        title_lbl.setObjectName("sectionTitle")
        main_layout.addWidget(title_lbl)

        # 2. KPI Stat Cards Row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(14)

        self.card_nodes = StatCard("ACTIVE SWARM NODES", "0")
        self.card_pending = StatCard("PENDING APPROVALS", "0")
        self.card_mode = StatCard("NETWORK TRANSPORT", "LAN (TCP)")
        self.card_channel = StatCard("ACTIVE CHANNEL", "None")

        stats_layout.addWidget(self.card_nodes)
        stats_layout.addWidget(self.card_pending)
        stats_layout.addWidget(self.card_mode)
        stats_layout.addWidget(self.card_channel)
        main_layout.addLayout(stats_layout)

        # 3. Server & Channel Control Card
        control_card = QFrame()
        control_card.setObjectName("cardSurface")
        control_layout = QVBoxLayout(control_card)
        control_layout.setContentsMargins(18, 16, 18, 16)
        control_layout.setSpacing(12)

        card_heading = QLabel("LAN Server & Channel Operations")
        card_heading.setObjectName("appTitle")
        control_layout.addWidget(card_heading)

        # Inputs Row
        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(10)

        # Mode dropdown
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["LAN (Local Wi-Fi)", "Internet (Raw TCP)"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        inputs_layout.addWidget(self.mode_combo)

        # Host IP Combo (All LAN interfaces recommended)
        self.host_combo = QComboBox()
        self.host_combo.setMinimumWidth(220)
        detected_ips = LANTransport.get_lan_ips()
        self.host_combo.addItem(f"0.0.0.0 (All LAN Adapters - {LANTransport.get_lan_ip()})", "0.0.0.0")
        for ip in detected_ips:
            if ip != "0.0.0.0":
                self.host_combo.addItem(f"{ip} (Wi-Fi / Ethernet)", ip)
        inputs_layout.addWidget(self.host_combo)

        # Port input
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("Port")
        self.port_input.setText("8765")
        self.port_input.setFixedWidth(70)
        inputs_layout.addWidget(self.port_input)

        # Primary Action Button
        self.btn_start_and_create = QPushButton("Start Server & Generate Invite")
        self.btn_start_and_create.setObjectName("primaryButton")
        self.btn_start_and_create.clicked.connect(self._handle_start_and_create)
        inputs_layout.addWidget(self.btn_start_and_create)

        self.btn_stop = QPushButton("Stop Server")
        self.btn_stop.setObjectName("dangerButton")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._handle_stop_server)
        inputs_layout.addWidget(self.btn_stop)

        control_layout.addLayout(inputs_layout)

        # Generated Bootstrap String Container
        self.bootstrap_box = QPlainTextEdit()
        self.bootstrap_box.setReadOnly(True)
        self.bootstrap_box.setFixedHeight(65)
        self.bootstrap_box.setPlaceholderText("Click 'Start Server & Generate Invite' to display your paste-ready friend bootstrap command...")
        self.bootstrap_box.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 11px;")
        control_layout.addWidget(self.bootstrap_box)

        # Copy & Status Bar
        copy_layout = QHBoxLayout()
        copy_layout.setSpacing(10)

        self.btn_copy = QPushButton("Copy Command to Clipboard")
        self.btn_copy.setObjectName("successButton")
        self.btn_copy.setEnabled(False)
        self.btn_copy.clicked.connect(self._copy_bootstrap)
        copy_layout.addWidget(self.btn_copy)

        self.lbl_bootstrap_status = QLabel("Server offline. Select mode and click Start Server.")
        self.lbl_bootstrap_status.setObjectName("subTitle")
        copy_layout.addWidget(self.lbl_bootstrap_status)

        copy_layout.addStretch()
        control_layout.addLayout(copy_layout)

        main_layout.addWidget(control_card)

        # 4. Connected Swarm Nodes Table Section
        table_header = QLabel("Swarm Nodes & Access Approvals")
        table_header.setObjectName("sectionTitle")
        main_layout.addWidget(table_header)

        self.node_table = NodeTableWidget()
        self.node_table.approve_requested.connect(self.approve_node_clicked.emit)
        self.node_table.reject_requested.connect(self.reject_node_clicked.emit)
        main_layout.addWidget(self.node_table)

    def _on_mode_changed(self, index: int):
        mode_str = "LAN (TCP)" if index == 0 else "Internet Mode"
        self.card_mode.set_value(mode_str)

    def _get_selected_host(self) -> str:
        idx = self.host_combo.currentIndex()
        data = self.host_combo.itemData(idx)
        if data:
            return data
        # Fallback to LAN IP
        return LANTransport.get_lan_ip()

    def _handle_start_and_create(self):
        host = self._get_selected_host()
        port_str = self.port_input.text().strip()
        if not port_str.isdigit():
            QMessageBox.warning(self, "Invalid Parameters", "Please enter a valid numeric port.")
            return

        mode = "lan" if self.mode_combo.currentIndex() == 0 else "internet"
        port = int(port_str)

        # 1. Start Server (0.0.0.0 binds all interfaces)
        self.start_server_clicked.emit(host, port, mode)

        # 2. Determine actual LAN IP address for remote devices
        adv_ip = host
        if host in ("0.0.0.0", "127.0.0.1", "localhost", ""):
            adv_ip = LANTransport.get_lan_ip()
        
        endpoint = f"{adv_ip}:{port}"

        # 3. Create Channel & Generate Invitation Command
        self.create_channel_clicked.emit(endpoint)

    def _handle_stop_server(self):
        self.stop_server_clicked.emit()
        self.bootstrap_box.clear()
        self.btn_copy.setEnabled(False)
        self.lbl_bootstrap_status.setText("Server stopped.")
        self.lbl_bootstrap_status.setStyleSheet("color: #EF4444; font-weight: bold;")

    def update_state(self, state: dict):
        running = state.get("server_running", False)
        self.btn_start_and_create.setText("Generate New Invite" if running else "Start Server & Generate Invite")
        self.btn_stop.setEnabled(running)

        active = state.get("active_nodes", [])
        pending = state.get("pending_nodes", [])

        self.card_nodes.set_value(f"{len(active):02d}")
        self.card_pending.set_value(f"{len(pending):02d}")
        self.card_channel.set_value(state.get("channel_id", "None"))

        self.node_table.populate(active, pending)

    def set_bootstrap_copied(self, bootstrap_cmd: str):
        self.bootstrap_payload = bootstrap_cmd
        self.bootstrap_box.setPlainText(bootstrap_cmd)
        QApplication.clipboard().setText(bootstrap_cmd)
        self.btn_copy.setEnabled(True)
        self.lbl_bootstrap_status.setText("✓ Server Online & Invitation Command Copied! Paste into PowerShell on friend's PC.")
        self.lbl_bootstrap_status.setStyleSheet("color: #10B981; font-weight: bold;")

    def _copy_bootstrap(self):
        if self.bootstrap_payload:
            QApplication.clipboard().setText(self.bootstrap_payload)
            QMessageBox.information(self, "Copied", "Copied python bootstrap command to clipboard!")
