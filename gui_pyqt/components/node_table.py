from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal, Qt


class NodeTableWidget(QTableWidget):
    """
    Elevated table showing active and pending swarm nodes.
    """
    approve_requested = pyqtSignal(str)
    reject_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Node Identifier", "Network Address", "Status", "Actions"])
        
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(46)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    def populate(self, active_nodes: list, pending_nodes: list):
        total = len(active_nodes) + len(pending_nodes)
        self.setRowCount(total)

        row = 0
        for node in pending_nodes:
            self._set_row(row, node["id"], node["addr"], "pending", is_pending=True)
            row += 1

        for node in active_nodes:
            self._set_row(row, node["id"], node["addr"], "accepted", is_pending=False)
            row += 1

    def _set_row(self, row: int, node_id: str, address: str, status_str: str, is_pending: bool):
        item_id = QTableWidgetItem(node_id)
        item_id.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.setItem(row, 0, item_id)

        item_addr = QTableWidgetItem(address)
        item_addr.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.setItem(row, 1, item_addr)

        status_lbl = QLabel(status_str.upper())
        status_lbl.setObjectName("statusPill")
        status_lbl.setProperty("status", "pending" if is_pending else "online")
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        container = QWidget()
        l = QHBoxLayout(container)
        l.setContentsMargins(4, 4, 4, 4)
        l.addWidget(status_lbl)
        self.setCellWidget(row, 2, container)

        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(6)

        if is_pending:
            btn_allow = QPushButton("Approve")
            btn_allow.setObjectName("successButton")
            btn_allow.setFixedWidth(80)
            btn_allow.clicked.connect(lambda checked, nid=node_id: self.approve_requested.emit(nid))
            action_layout.addWidget(btn_allow)

            btn_reject = QPushButton("Reject")
            btn_reject.setObjectName("dangerButton")
            btn_reject.setFixedWidth(70)
            btn_reject.clicked.connect(lambda checked, nid=node_id: self.reject_requested.emit(nid))
            action_layout.addWidget(btn_reject)
        else:
            lbl_accepted = QLabel("Connected")
            lbl_accepted.setStyleSheet("color: #10B981; font-weight: bold; font-size: 12px;")
            action_layout.addWidget(lbl_accepted)

        self.setCellWidget(row, 3, action_widget)
