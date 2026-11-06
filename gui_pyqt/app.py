import sys
import os

# Ensure project root is in sys.path when running file directly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QStackedWidget, QInputDialog, QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from gui_pyqt.bridge import SwarmBridge
from gui_pyqt.components.header import HeaderBar
from gui_pyqt.components.sidebar import Sidebar
from gui_pyqt.views.dashboard_view import DashboardView
from gui_pyqt.views.channels_view import ChannelsView
from gui_pyqt.views.nodes_view import NodesView
from gui_pyqt.views.tasks_view import TasksView
from gui_pyqt.views.logs_view import LogsView
from gui_pyqt.views.skills_view import SkillsView


class SHACMainWindow(QMainWindow):
    """
    Main Application Window with Microsoft 365 Enterprise White Fluent Theme.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SHAC // Enterprise Swarm Intelligence Control")
        self.resize(1240, 820)
        self.setMinimumSize(980, 640)

        # Initialize Bridge & Security
        self.bridge = SwarmBridge()

        # Load Stylesheet
        self._load_stylesheet()

        # Center on screen
        self._center_on_screen()

        # Check Master Token Auth
        if not self._authenticate_master():
            sys.exit(1)

        # Build Main Frame & Layout
        central_widget = QWidget()
        central_widget.setObjectName("mainCanvas")
        self.setCentralWidget(central_widget)

        app_layout = QVBoxLayout(central_widget)
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(0)

        # 1. Top Header Bar
        self.header = HeaderBar()
        app_layout.addWidget(self.header)

        # 2. Main Content Split (Sidebar + Stacked Pages View)
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Left Vertical Navigation Sidebar
        self.sidebar = Sidebar()
        body_layout.addWidget(self.sidebar)

        # Pages View Container (StackedWidget)
        self.stacked_pages = QStackedWidget()

        # 6 Dedicated Distinct Views
        self.dashboard_view = DashboardView()
        self.channels_view = ChannelsView()
        self.nodes_view = NodesView(self.bridge)
        self.tasks_view = TasksView()
        self.logs_view = LogsView()
        self.logs_view.parent_app = self
        self.skills_view = SkillsView(self.bridge)

        self.stacked_pages.addWidget(self.dashboard_view)    # Index 0: Dashboard Overview
        self.stacked_pages.addWidget(self.channels_view)     # Index 1: Dedicated Channels Manager
        self.stacked_pages.addWidget(self.nodes_view)        # Index 2: Dedicated Nodes & Cyber Terminal
        self.stacked_pages.addWidget(self.tasks_view)        # Index 3: Consented Task Dispatcher
        self.stacked_pages.addWidget(self.logs_view)         # Index 4: Realtime Audit & Console Logs
        self.stacked_pages.addWidget(self.skills_view)       # Index 5: Swarm Skills & Automation Manager (200+)

        body_layout.addWidget(self.stacked_pages)
        app_layout.addWidget(body_widget)

        # Connect Navigation
        self.sidebar.page_changed.connect(self.stacked_pages.setCurrentIndex)

        # Connect Dashboard & Channels Signals to Bridge
        self.dashboard_view.start_server_clicked.connect(self.bridge.start_server)
        self.dashboard_view.stop_server_clicked.connect(self.bridge.stop_server)
        self.dashboard_view.create_channel_clicked.connect(self._handle_create_channel)
        self.dashboard_view.approve_node_clicked.connect(self.bridge.approve_node)
        self.dashboard_view.reject_node_clicked.connect(self.bridge.reject_node)

        self.channels_view.create_channel_clicked.connect(self._handle_create_channel_from_view)

        self.nodes_view.approve_node_clicked.connect(self.bridge.approve_node)
        self.nodes_view.reject_node_clicked.connect(self.bridge.reject_node)

        # Connect Tasks View Signals
        self.tasks_view.dispatch_task_clicked.connect(self.bridge.send_task)

        # Connect Bridge Signals to UI Updates
        self.bridge.log_emitted.connect(self.logs_view.append_log)
        self.bridge.state_updated.connect(self._on_state_updated)
        self.bridge.task_response_received.connect(self.tasks_view.add_audit_record)

        self.bridge.log_emitted.emit("SUCCESS", "SHAC Enterprise Control GUI initialized with 6 dedicated views.")

    def _load_stylesheet(self):
        style_path = os.path.join(os.path.dirname(__file__), "styles", "fluent_light.qss")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            win_geo = self.frameGeometry()
            win_geo.moveCenter(screen_geo.center())
            self.move(win_geo.topLeft())

    def _authenticate_master(self) -> bool:
        auth = self.bridge.admin_auth
        if not auth.exists():
            token = auth.create()
            self.bridge.admin_token = token
            self.bridge.admin_authenticated = True
            QMessageBox.information(
                self,
                "SHAC Master Owner Token Created",
                f"A new master owner token has been created:\n\n{token}\n\nSave this token securely."
            )
            return True

        token, ok = QInputDialog.getText(
            self,
            "SHAC Master Owner Authentication",
            "Enter your SHAC master security token:",
            QLineEdit.EchoMode.Password
        )
        if not ok or not token:
            return False

        if self.bridge.authenticate_admin(token):
            return True
        else:
            QMessageBox.critical(self, "Access Denied", "Invalid SHAC master security token.")
            return False

    def _handle_create_channel(self, endpoint: str):
        bootstrap_cmd = self.bridge.create_channel(endpoint)
        if bootstrap_cmd:
            self.dashboard_view.set_bootstrap_copied(bootstrap_cmd)
            ch_id = self.bridge.channel.channel_id if self.bridge.channel else "N/A"
            cred = self.bridge.channel.credential if self.bridge.channel else "N/A"
            self.channels_view.on_channel_created(ch_id, cred, "lan", endpoint, bootstrap_cmd)

    def _handle_create_channel_from_view(self, endpoint: str, mode: str):
        bootstrap_cmd = self.bridge.create_channel(endpoint)
        if bootstrap_cmd:
            self.dashboard_view.set_bootstrap_copied(bootstrap_cmd)
            ch_id = self.bridge.channel.channel_id if self.bridge.channel else "N/A"
            cred = self.bridge.channel.credential if self.bridge.channel else "N/A"
            self.channels_view.on_channel_created(ch_id, cred, mode, endpoint, bootstrap_cmd)

    def _on_state_updated(self, state: dict):
        running = state.get("server_running", False)
        host = state.get("host", "")
        port = state.get("port", 8765)
        endpoint = f"{host}:{port}" if host else ""

        self.header.update_status(running, endpoint)
        self.dashboard_view.update_state(state)
        
        active = state.get("active_nodes", [])
        pending = state.get("pending_nodes", [])
        self.nodes_view.update_nodes(active, pending)
        self.skills_view.update_nodes(active)

    def closeEvent(self, event):
        if self.bridge.server_running:
            self.bridge.stop_server()
        event.accept()


def main():
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"
    
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    app = QApplication(sys.argv)
    window = SHACMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
