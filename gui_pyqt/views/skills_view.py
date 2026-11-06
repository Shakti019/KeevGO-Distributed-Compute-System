import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
    QPushButton, QFrame, QMessageBox, QTableWidget, QTableWidgetItem, 
    QHeaderView, QPlainTextEdit, QSplitter, QDialog, QFormLayout
)
from PyQt6.QtCore import pyqtSignal, Qt
from skills.skills_manager import SkillsManager


class SkillsView(QWidget):
    """
    Dedicated Swarm Skills & Automation Manager View.
    Supports browsing 200+ automation skills, target node selection, 
    parameter customization, custom template creation, and live 2-way output streaming.
    """
    dispatch_skill_clicked = pyqtSignal(str, str, dict)  # (target_node, action, params)

    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.skills_manager = SkillsManager()
        self.selected_skill = None
        self.active_nodes = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header Title Row
        header_row = QHBoxLayout()
        title_lbl = QLabel("Swarm Skills & Automation Engine (200+ Catalog)")
        title_lbl.setObjectName("sectionTitle")
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        self.btn_create_custom = QPushButton("+ Create Custom Skill")
        self.btn_create_custom.setObjectName("successButton")
        self.btn_create_custom.clicked.connect(self._open_create_dialog)
        header_row.addWidget(self.btn_create_custom)
        layout.addLayout(header_row)

        # Main Splitter (Left: Skill Catalog | Right: Execution & Two-Way Response Panel)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- LEFT PANEL: SKILL CATALOG ---
        left_card = QFrame()
        left_card.setObjectName("cardSurface")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(10)

        # Search and Category Filter
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search 200+ skills...")
        self.search_input.textChanged.connect(self._filter_skills)
        filter_row.addWidget(self.search_input)

        self.cat_combo = QComboBox()
        self.cat_combo.addItem("All Categories")
        self.cat_combo.addItems(self.skills_manager.get_categories())
        self.cat_combo.currentIndexChanged.connect(self._filter_skills)
        filter_row.addWidget(self.cat_combo)

        left_layout.addLayout(filter_row)

        # Skill Table
        self.skills_table = QTableWidget()
        self.skills_table.setColumnCount(3)
        self.skills_table.setHorizontalHeaderLabels(["Skill Name", "Category", "Action"])
        self.skills_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.skills_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.skills_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.skills_table.verticalHeader().setVisible(False)
        self.skills_table.verticalHeader().setDefaultSectionSize(40)
        self.skills_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.skills_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.skills_table.itemSelectionChanged.connect(self._on_skill_selected)
        left_layout.addWidget(self.skills_table)

        splitter.addWidget(left_card)

        # --- RIGHT PANEL: DISPATCHER & TWO-WAY OUTPUT ---
        right_card = QFrame()
        right_card.setObjectName("cardSurface")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        self.lbl_selected_title = QLabel("Select a skill from the catalog to configure...")
        self.lbl_selected_title.setObjectName("appTitle")
        right_layout.addWidget(self.lbl_selected_title)

        self.lbl_selected_desc = QLabel("")
        self.lbl_selected_desc.setObjectName("subTitle")
        self.lbl_selected_desc.setWordWrap(True)
        right_layout.addWidget(self.lbl_selected_desc)

        # Target Node & Parameter Inputs
        form_row = QHBoxLayout()
        form_row.setSpacing(8)

        form_row.addWidget(QLabel("Target Node:"))
        self.node_combo = QComboBox()
        self.node_combo.addItem("ALL NODES (Broadcast)", "all")
        form_row.addWidget(self.node_combo)

        right_layout.addLayout(form_row)

        # Arguments Editor (JSON)
        right_layout.addWidget(QLabel("Skill Arguments (JSON):"))
        self.args_edit = QPlainTextEdit()
        self.args_edit.setFixedHeight(110)
        self.args_edit.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 12px;")
        right_layout.addWidget(self.args_edit)

        # Run Button
        self.btn_run = QPushButton("DISPATCH SKILL TO SWARM")
        self.btn_run.setObjectName("primaryButton")
        self.btn_run.setMinimumHeight(38)
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self._dispatch_selected_skill)
        right_layout.addWidget(self.btn_run)

        # Live Two-Way Output Display
        right_layout.addWidget(QLabel("Real-Time Execution Response (Stdout / Stderr):"))
        self.output_box = QPlainTextEdit()
        self.output_box.setReadOnly(True)
        self.output_box.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; background-color: #050810; color: #00FF9D; padding: 8px;")
        right_layout.addWidget(self.output_box)

        splitter.addWidget(right_card)
        splitter.setSizes([500, 600])

        layout.addWidget(splitter)

        # Connect Bridge Response Signal
        if self.bridge:
            self.bridge.task_response_received.connect(self.on_task_response)

        # Populate Initial Table
        self._populate_skills(self.skills_manager.list_skills())

    def update_nodes(self, active_nodes: list):
        self.active_nodes = active_nodes
        self.node_combo.clear()
        self.node_combo.addItem("ALL NODES (Broadcast)", "all")
        for node in active_nodes:
            nid = node.get("id", "")
            addr = node.get("addr", "")
            self.node_combo.addItem(f"{nid} ({addr})", nid)

    def _populate_skills(self, skill_list: list):
        self.skills_table.setRowCount(len(skill_list))
        for r, skill in enumerate(skill_list):
            item_name = QTableWidgetItem(skill.get("name", "Skill"))
            item_cat = QTableWidgetItem(skill.get("category", "General"))
            item_act = QTableWidgetItem(skill.get("action", ""))

            # Store skill ID in user data
            item_name.setData(Qt.ItemDataRole.UserRole, skill.get("id"))

            self.skills_table.setItem(r, 0, item_name)
            self.skills_table.setItem(r, 1, item_cat)
            self.skills_table.setItem(r, 2, item_act)

    def _filter_skills(self):
        query = self.search_input.text().strip().lower()
        cat_idx = self.cat_combo.currentIndex()
        selected_cat = self.cat_combo.currentText() if cat_idx > 0 else None

        all_skills = self.skills_manager.list_skills()
        filtered = []
        for s in all_skills:
            match_query = not query or (query in s.get("name", "").lower() or query in s.get("id", "").lower() or query in s.get("description", "").lower())
            match_cat = not selected_cat or s.get("category") == selected_cat
            if match_query and match_cat:
                filtered.append(s)

        self._populate_skills(filtered)

    def _on_skill_selected(self):
        rows = self.skills_table.selectedItems()
        if not rows:
            return
        skill_id = self.skills_table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        skill = self.skills_manager.get_skill(skill_id)
        if skill:
            self.selected_skill = skill
            self.lbl_selected_title.setText(f"{skill.get('name')}  [{skill.get('id')}]")
            self.lbl_selected_desc.setText(skill.get("description", ""))
            self.args_edit.setPlainText(json.dumps(skill.get("arguments", {}), indent=2))
            self.btn_run.setEnabled(True)

    def _dispatch_selected_skill(self):
        if not self.selected_skill:
            return
        
        try:
            params = json.loads(self.args_edit.toPlainText().strip() or "{}")
        except Exception as e:
            QMessageBox.warning(self, "Invalid JSON", f"Skill arguments must be valid JSON: {e}")
            return

        target_idx = self.node_combo.currentIndex()
        target_node = self.node_combo.itemData(target_idx) or "all"
        action = self.selected_skill.get("action", "unknown")

        self.output_box.appendPlainText(f"\n[DISPATCH] Skill '{self.selected_skill.get('name')}' ({action}) -> Target: '{target_node}'")
        self.output_box.appendPlainText(f"[PARAMS] {params}")
        self.output_box.appendPlainText("[STATUS] Waiting for remote node consent & execution response...")

        self.dispatch_skill_clicked.emit(target_node, action, params)
        if self.bridge:
            self.bridge.send_task(target_node, action, params)

    def on_task_response(self, resp: dict):
        status = resp.get("status", "unknown").upper()
        nid = resp.get("node_id", "node")
        name = resp.get("node_name", nid)
        result = resp.get("result", "")
        stdout = resp.get("stdout", "")
        stderr = resp.get("stderr", "")

        self.output_box.appendPlainText(f"\n=== [RESPONSE FROM {name} ({nid})] ===")
        self.output_box.appendPlainText(f"STATUS: {status} | RESULT: {result}")
        if stdout:
            self.output_box.appendPlainText(f"--- STDOUT ---\n{stdout}")
        if stderr:
            self.output_box.appendPlainText(f"--- STDERR ---\n{stderr}")
        self.output_box.appendPlainText("=" * 45)

    def _open_create_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Custom Swarm Skill")
        dialog.resize(500, 380)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        txt_id = QLineEdit()
        txt_id.setPlaceholderText("custom.my_automation")
        form.addRow("Skill ID:", txt_id)

        txt_name = QLineEdit()
        txt_name.setPlaceholderText("My Custom Automation")
        form.addRow("Skill Name:", txt_name)

        txt_desc = QLineEdit()
        txt_desc.setPlaceholderText("Description of what this skill performs")
        form.addRow("Description:", txt_desc)

        txt_cat = QLineEdit()
        txt_cat.setText("Custom")
        form.addRow("Category:", txt_cat)

        combo_act = QComboBox()
        combo_act.addItems(["python.exec", "shell.exec", "git.clone", "file.create", "file.read", "file.write", "file.delete", "file.list", "browser.search", "http.fetch"])
        form.addRow("Action Type:", combo_act)

        txt_args = QPlainTextEdit()
        txt_args.setPlainText('{\n  "code": "print(\'Hello Custom Skill!\')"\n}')
        form.addRow("Default Args (JSON):", txt_args)

        layout.addLayout(form)

        btn_save = QPushButton("Save Skill")
        btn_save.setObjectName("primaryButton")
        
        def save():
            sid = txt_id.text().strip()
            sname = txt_name.text().strip()
            sdesc = txt_desc.text().strip()
            scat = txt_cat.text().strip()
            sact = combo_act.currentText()
            try:
                sargs = json.loads(txt_args.toPlainText().strip() or "{}")
            except Exception as e:
                QMessageBox.warning(dialog, "Error", f"Invalid JSON args: {e}")
                return

            if not sid or not sname:
                QMessageBox.warning(dialog, "Error", "Fill ID and Name.")
                return

            self.skills_manager.create_custom_skill(sid, sname, sdesc, scat, sact, sargs)
            self._filter_skills()
            QMessageBox.information(dialog, "Success", f"Skill '{sname}' created!")
            dialog.accept()

        btn_save.clicked.connect(save)
        layout.addWidget(btn_save)

        dialog.exec()
