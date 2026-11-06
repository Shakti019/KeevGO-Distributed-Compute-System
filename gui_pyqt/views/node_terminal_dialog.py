from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit, 
    QLineEdit, QPushButton, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt
from gui_pyqt.views.screen_mirror_dialog import ScreenMirrorWindow


class NodeTerminalWindow(QDialog):
    """
    Dedicated Cyber/Linux-style Dark Terminal Window for communicating 
    and executing high-level tasks on an individual Swarm Node.
    """
    def __init__(self, node_id: str, address: str, bridge, parent=None):
        super().__init__(parent)
        self.node_id = node_id
        self.address = address
        self.bridge = bridge
        self.mirror_window = None

        self.setWindowTitle(f"Dedicated CLI // Node {node_id} ({address})")
        self.resize(900, 560)
        self.setMinimumSize(680, 420)
        
        # Dark Cyber Styling
        self.setStyleSheet("""
            QDialog {
                background-color: #090D16;
                color: #00FF9D;
            }
            QLabel {
                color: #00F0FF;
                font-family: 'Consolas', 'Courier New', monospace;
                font-weight: bold;
            }
            QPlainTextEdit {
                background-color: #050810;
                color: #00FF9D;
                border: 1px solid #1E293B;
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                padding: 10px;
            }
            QLineEdit {
                background-color: #0F172A;
                color: #FFFFFF;
                border: 1px solid #00F0FF;
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border: 2px solid #00FF9D;
            }
            QPushButton {
                background-color: #00F0FF;
                color: #090D16;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 8px 16px;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            QPushButton:hover {
                background-color: #00FF9D;
            }
            QPushButton:pressed {
                background-color: #00C875;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Info Bar
        header = QHBoxLayout()
        header.addWidget(QLabel(f"[NODE DEDICATED CLI] {node_id} @ {address}"))
        header.addStretch()
        
        self.btn_screen_mirror = QPushButton("📺 SCREEN MIRROR")
        self.btn_screen_mirror.setStyleSheet("background-color: #0EA5E9; color: #FFFFFF;")
        self.btn_screen_mirror.clicked.connect(self._open_mirror_window)
        header.addWidget(self.btn_screen_mirror)

        self.btn_script_editor = QPushButton("📜 PASTE & RUN SCRIPT / CODE")
        self.btn_script_editor.setStyleSheet("background-color: #10B981; color: #FFFFFF;")
        self.btn_script_editor.clicked.connect(self._open_script_editor_dialog)
        header.addWidget(self.btn_script_editor)

        layout.addLayout(header)

        # Output Text Pane
        self.terminal_output = QPlainTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.appendPlainText(
            f"--- SHAC DEDICATED SWARM TERMINAL ---\n"
            f"Target Node: {node_id}\n"
            f"Address:     {address}\n"
            f"Commands:    system.info, file.list, shell <cmd>, git.clone <url>, browser.search <q>, python <code>, help\n"
            f"---------------------------------------------------\n"
        )
        layout.addWidget(self.terminal_output)

        # Prompt Input Row
        prompt_row = QHBoxLayout()
        prompt_row.setSpacing(8)

        self.prompt_label = QLabel(f"master@{node_id.lower()}:~$ ")
        prompt_row.addWidget(self.prompt_label)

        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Type command or query (e.g. system.info, shell dir, git.clone <url>, browser.search)...")
        self.cmd_input.returnPressed.connect(self._execute_command)
        prompt_row.addWidget(self.cmd_input)

        self.btn_send = QPushButton("SEND")
        self.btn_send.clicked.connect(self._execute_command)
        prompt_row.addWidget(self.btn_send)

        layout.addLayout(prompt_row)

        # Connect Bridge Task Response Signal
        if self.bridge:
            self.bridge.task_response_received.connect(self.on_task_response)

    def on_task_response(self, resp: dict):
        target_nid = resp.get("node_id", "")
        if target_nid and target_nid != self.node_id:
            return  # Filter response to current node

        status = resp.get("status", "unknown").upper()
        result = resp.get("result", "")
        stdout = resp.get("stdout", "")
        stderr = resp.get("stderr", "")

        self.terminal_output.appendPlainText(f"\n<<< [REMOTE RESPONSE FROM {self.node_id}] STATUS: {status} | RESULT: {result}")
        if stdout:
            self.terminal_output.appendPlainText(f"[STDOUT]\n{stdout}")
        if stderr:
            self.terminal_output.appendPlainText(f"[STDERR]\n{stderr}")
        self.terminal_output.appendPlainText("-" * 50)

    def _execute_command(self):
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        
        self.cmd_input.clear()
        self.terminal_output.appendPlainText(f"master@{self.node_id.lower()}:~$ {cmd}")

        if cmd.lower() in ("help", "?"):
            self.terminal_output.appendPlainText(
                "  Available Node Terminal Commands:\n"
                "    system.info             - Inspect remote OS platform & CPU\n"
                "    file.list [dir]         - List directory files\n"
                "    shell <cmd>             - Execute shell/cmd/powershell command\n"
                "    git.clone <url> [dir]   - Clone remote repository\n"
                "    python <code>           - Run Python code snippet\n"
                "    browser.search <query>  - Audited search task\n"
                "    clear                   - Clear display\n"
            )
            return

        if cmd.lower() == "clear":
            self.terminal_output.clear()
            return

        if cmd.lower() == "system.info":
            action = "system.info"
            params = {}
        elif cmd.startswith("file.list"):
            path = cmd[9:].strip() or "."
            action = "file.list"
            params = {"path": path}
        elif cmd.startswith("shell "):
            command_str = cmd[6:].strip()
            action = "shell.exec"
            params = {"command": command_str}
        elif cmd.startswith("git.clone "):
            repo_url = cmd[10:].strip()
            action = "git.clone"
            params = {"repo_url": repo_url, "target_dir": "projects/cloned_repo"}
        elif cmd.startswith("python "):
            code_str = cmd[7:].strip()
            action = "python.exec"
            params = {"code": code_str}
        elif cmd.startswith("browser.search "):
            query = cmd[15:].strip()
            action = "browser.search"
            params = {"query": query}
        else:
            # Default unmatched commands to python code execution if it looks like code or fallback to shell
            action = "python.exec"
            params = {"code": cmd}

        self.bridge.send_task(self.node_id, action, params)
        self.terminal_output.appendPlainText(f"[DISPATCH TASK] Action: '{action}' | Params: {params}")

    def _open_script_editor_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Share / Execute Script on Node {self.node_id}")
        dialog.resize(750, 480)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Paste / Write Unlimited Multi-Line Code or Script Payload:"))

        editor = QPlainTextEdit()
        editor.setPlaceholderText("# Paste your Python code, PowerShell script, or text of any length here...\nprint('Executing remote script on node!')")
        editor.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; background-color: #050810; color: #00FF9D; padding: 10px;")
        layout.addWidget(editor)

        opt_row = QHBoxLayout()
        opt_row.addWidget(QLabel("Execution Engine:"))
        combo_mode = QComboBox()
        combo_mode.addItem("Python Script Execution (python.exec)", "python.exec")
        combo_mode.addItem("Shell / Terminal Command (shell.exec)", "shell.exec")
        combo_mode.addItem("Save File to Remote Disk (file.create)", "file.create")
        opt_row.addWidget(combo_mode)

        layout.addLayout(opt_row)

        file_path_input = QLineEdit()
        file_path_input.setPlaceholderText("Target file path (e.g. scripts/my_script.py)...")
        file_path_input.setText("scripts/remote_script.py")
        layout.addWidget(file_path_input)

        btn_run = QPushButton("DISPATCH SCRIPT TO NODE")
        btn_run.setObjectName("primaryButton")

        def run_script():
            text_payload = editor.toPlainText().strip()
            if not text_payload:
                QMessageBox.warning(dialog, "Error", "Paste or write script text before dispatching.")
                return

            mode = combo_mode.currentData()
            if mode == "python.exec":
                action = "python.exec"
                params = {"code": text_payload}
            elif mode == "shell.exec":
                action = "shell.exec"
                params = {"command": text_payload}
            else:
                action = "file.create"
                params = {"path": file_path_input.text().strip() or "remote_file.txt", "content": text_payload}

            self.bridge.send_task(self.node_id, action, params)
            self.terminal_output.appendPlainText(f"\n[DISPATCH SCRIPT] Sent {len(text_payload)} characters via {action} to {self.node_id}")
            dialog.accept()

        btn_run.clicked.connect(run_script)
        layout.addWidget(btn_run)

        dialog.exec()

    def _open_mirror_window(self):
        if not self.mirror_window or not self.mirror_window.isVisible():
            self.mirror_window = ScreenMirrorWindow(self.node_id, self.address, self.bridge, self)
            self.mirror_window.show()
        else:
            self.mirror_window.raise_()
            self.mirror_window.activateWindow()
