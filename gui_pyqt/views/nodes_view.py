from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, 
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import pyqtSignal, Qt
from gui_pyqt.views.node_terminal_dialog import NodeTerminalWindow
from gui_pyqt.views.screen_mirror_dialog import ScreenMirrorWindow


class NodesView(QWidget):
    """
    Dedicated Swarm Nodes & Approvals View with individual node cyber terminal access
    and remote visual screen mirroring.
    """
    approve_node_clicked = pyqtSignal(str)
    reject_node_clicked = pyqtSignal(str)

    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.open_terminals = {}
        self.open_mirrors = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header Title
        title_lbl = QLabel("Connected Swarm Nodes, Dedicated CLI & Visual Screen Mirror")
        title_lbl.setObjectName("sectionTitle")
        layout.addWidget(title_lbl)

        # Pending Requests Section Card
        pending_card = QFrame()
        pending_card.setObjectName("cardSurface")
        pending_layout = QVBoxLayout(pending_card)
        pending_layout.setContentsMargins(18, 16, 18, 16)
        pending_layout.setSpacing(10)

        pending_title = QLabel("Pending Access Requests")
        pending_title.setObjectName("appTitle")
        pending_layout.addWidget(pending_title)

        self.pending_table = QTableWidget()
        self.pending_table.setColumnCount(3)
        self.pending_table.setHorizontalHeaderLabels(["Request / Node ID", "Details", "Action"])
        self.pending_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.pending_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.pending_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.pending_table.verticalHeader().setVisible(False)
        self.pending_table.verticalHeader().setDefaultSectionSize(48)
        self.pending_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.pending_table.setMinimumHeight(160)
        pending_layout.addWidget(self.pending_table)

        layout.addWidget(pending_card)

        # Active Connected Nodes Section
        active_title = QLabel("Accepted Swarm Nodes")
        active_title.setObjectName("sectionTitle")
        layout.addWidget(active_title)

        self.active_table = QTableWidget()
        self.active_table.setColumnCount(4)
        self.active_table.setHorizontalHeaderLabels(["Node ID", "Address", "Status", "Actions & Controls"])
        self.active_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.active_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.active_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.active_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.active_table.verticalHeader().setVisible(False)
        self.active_table.verticalHeader().setDefaultSectionSize(48)
        self.active_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.active_table)

    def update_nodes(self, active_nodes: list, pending_nodes: list):
        # Update Pending Table
        self.pending_table.setRowCount(len(pending_nodes))
        for r, node in enumerate(pending_nodes):
            nid = node.get("id", "")
            addr = node.get("addr", "")
            self.pending_table.setItem(r, 0, QTableWidgetItem(nid))
            self.pending_table.setItem(r, 1, QTableWidgetItem(addr))

            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(6, 4, 6, 4)
            l.setSpacing(8)
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_app = QPushButton("Approve")
            btn_app.setObjectName("successButton")
            btn_app.setMinimumHeight(32)
            btn_app.setMinimumWidth(85)
            btn_app.clicked.connect(lambda checked, req_id=nid: self.approve_node_clicked.emit(req_id))
            l.addWidget(btn_app)

            btn_rej = QPushButton("Reject")
            btn_rej.setObjectName("dangerButton")
            btn_rej.setMinimumHeight(32)
            btn_rej.setMinimumWidth(75)
            btn_rej.clicked.connect(lambda checked, req_id=nid: self.reject_node_clicked.emit(req_id))
            l.addWidget(btn_rej)
            self.pending_table.setCellWidget(r, 2, w)

        # Update Active Table
        self.active_table.setRowCount(len(active_nodes))
        for r, node in enumerate(active_nodes):
            nid = node.get("id", "")
            addr = node.get("addr", "")
            self.active_table.setItem(r, 0, QTableWidgetItem(nid))
            self.active_table.setItem(r, 1, QTableWidgetItem(addr))

            lbl_st = QLabel("CONNECTED")
            lbl_st.setObjectName("statusPill")
            lbl_st.setProperty("status", "online")
            lbl_st.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            cw = QWidget()
            cl = QHBoxLayout(cw)
            cl.setContentsMargins(6, 4, 6, 4)
            cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(lbl_st)
            self.active_table.setCellWidget(r, 2, cw)

            # Open Dedicated Terminal & Screen Mirror Buttons
            tw = QWidget()
            tl = QHBoxLayout(tw)
            tl.setContentsMargins(6, 4, 6, 4)
            tl.setSpacing(6)
            tl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_term = QPushButton("Open Dedicated CLI")
            btn_term.setObjectName("primaryButton")
            btn_term.setMinimumHeight(32)
            btn_term.setMinimumWidth(140)
            btn_term.clicked.connect(lambda checked, n_id=nid, n_addr=addr: self._open_node_terminal(n_id, n_addr))
            tl.addWidget(btn_term)

            btn_mirror = QPushButton("📺 Screen Mirror")
            btn_mirror.setObjectName("successButton")
            btn_mirror.setMinimumHeight(32)
            btn_mirror.setMinimumWidth(130)
            btn_mirror.clicked.connect(lambda checked, n_id=nid, n_addr=addr: self._open_screen_mirror(n_id, n_addr))
            tl.addWidget(btn_mirror)

            self.active_table.setCellWidget(r, 3, tw)

    def _open_node_terminal(self, node_id: str, address: str):
        if node_id not in self.open_terminals or not self.open_terminals[node_id].isVisible():
            term = NodeTerminalWindow(node_id, address, self.bridge, self)
            self.open_terminals[node_id] = term
            term.show()
        else:
            self.open_terminals[node_id].raise_()
            self.open_terminals[node_id].activateWindow()

    def _open_screen_mirror(self, node_id: str, address: str):
        if node_id not in self.open_mirrors or not self.open_mirrors[node_id].isVisible():
            mirror = ScreenMirrorWindow(node_id, address, self.bridge, self)
            self.open_mirrors[node_id] = mirror
            mirror.show()
        else:
            self.open_mirrors[node_id].raise_()
            self.open_mirrors[node_id].activateWindow()
