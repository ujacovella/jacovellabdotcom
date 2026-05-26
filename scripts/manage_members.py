"""
Manage Group Members — PyQt6 GUI editor for members.
Generates group.html and theses.html from JSON data in assets/members/.
"""

import sys
import os
import re
import json
import shutil
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QTextEdit, QPushButton,
    QComboBox, QCheckBox, QListWidget, QListWidgetItem, QScrollArea,
    QGroupBox, QFrame, QMessageBox, QFileDialog, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_FILE = os.path.join(BASE_DIR, "group.html")
THESES_FILE = os.path.join(BASE_DIR, "theses.html")
MEMBERS_DIR = os.path.join(BASE_DIR, "assets", "members")
PHOTOS_DIR = os.path.join(BASE_DIR, "assets", "group")

ROLE_OPTIONS = ["PhD Student", "Postdoctoral Fellow", "Master Student", "Bachelor Student", "Other"]


def slugify(text):
    s = text.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s[:50] or "member"


def load_member(filename):
    with open(os.path.join(MEMBERS_DIR, filename), 'r', encoding='utf-8') as f:
        return json.load(f)


def save_member(filename, data):
    with open(os.path.join(MEMBERS_DIR, filename), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def delete_member_file(filename):
    path = os.path.join(MEMBERS_DIR, filename)
    if os.path.exists(path):
        os.remove(path)


def list_members():
    os.makedirs(MEMBERS_DIR, exist_ok=True)
    files = sorted([f for f in os.listdir(MEMBERS_DIR) if f.endswith('.json')])
    result = []
    for f in files:
        try:
            data = load_member(f)
            result.append((f, data))
        except:
            result.append((f, {"given": "[error]", "last": "", "role": ""}))
    return result


def format_name(data):
    given = data.get("given", "")
    middle = data.get("middle", "")
    last = data.get("last", "")
    parts = [p for p in [given, middle, last] if p]
    return " ".join(parts)


def get_initials(data):
    given = data.get("given", "")
    middle = data.get("middle", "")
    last = data.get("last", "")
    initials = ""
    if given:
        initials += given[0].upper()
    if middle:
        initials += middle[0].upper()
    if last:
        initials += last[0].upper()
    return initials


def escape_html(text):
    text = str(text)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&#39;")
    return text


MEMBER_COLORS = [
    ("#dce8f8", "#1a4080"),
    ("#d8f0e4", "#1a5c38"),
    ("#fef0d4", "#7a4a0a"),
    ("#f3e5f5", "#4a148c"),
    ("#ffebee", "#b71c1c"),
]

ALUMNI_BG = "#f5f5f7"
ALUMNI_FG = "#86868b"


def generate_card_html(data, filename):
    given = data.get("given", "")
    middle = data.get("middle", "")
    last = data.get("last", "")
    title = data.get("title", "")
    role = data.get("role", "")
    is_alumni = data.get("alumni", False)
    email = data.get("email", "")
    master = data.get("master", "")
    phd = data.get("phd", "")
    project = data.get("project", "")
    photo = data.get("photo", "")
    thesis_title = data.get("thesis_title", "")
    name = format_name(data)
    display_name = f"{title} {name}".strip() if title else name
    initials = get_initials(data)
    if is_alumni:
        bg_color = ALUMNI_BG
        text_color = ALUMNI_FG
        opacity_style = ' style="opacity: 0.7;"'
    else:
        c_idx = len(name) % len(MEMBER_COLORS)
        bg_color, text_color = MEMBER_COLORS[c_idx]
        opacity_style = ''
    lines = []
    lines.append(f'        <!-- MEMBER START: {name} -->')
    lines.append(f'        <div class="member-card" data-pi="false" data-alumni="{str(is_alumni).lower()}"{opacity_style}>')
    if photo:
        web_path = photo.replace("\\", "/")
        lines.append(f'          <img src="{web_path}" alt="{name}" class="member-avatar" style="object-fit: cover;">')
    else:
        lines.append(f'          <div class="member-avatar" style="background:{bg_color};color:{text_color}">{initials}</div>')
    lines.append(f'          <div class="member-name">{escape_html(display_name)}</div>')
    lines.append(f'          <div class="member-role">{escape_html(role)}</div>')
    lines.append(f'          <div class="member-details">')
    lines.append(f'            <p class="detail-email">{escape_html(email)}</p>')
    lines.append(f'            <p class="detail-master">{escape_html(master)}</p>')
    lines.append(f'            <p class="detail-phd">{escape_html(phd)}</p>')
    lines.append(f'            <p class="detail-project">{escape_html(project)}</p>')
    lines.append(f'          </div>')
    lines.append(f'        </div>')
    lines.append(f'        <!-- MEMBER END: {name} -->')
    return "\n".join(lines)


def generate_thesis_entry_html(data):
    thesis_title = data.get("thesis_title", "")
    thesis_link = data.get("thesis_link", "")
    phd_completed = data.get("phd_completed", False)
    if not thesis_title:
        return "", ""
    name = format_name(data)
    href_attr = f' href="{thesis_link}" target="_blank" rel="noopener noreferrer"' if thesis_link else ""
    tag = "a" if thesis_link else "span"
    link_style = 'text-decoration: none; color: var(--accent);' if thesis_link else 'color: var(--text);'
    entry = f'''            <div class="thesis-entry">
              <strong>{escape_html(name)}</strong><br>
              <{tag}{href_attr} style="{link_style} font-size: 14px;">"{escape_html(thesis_title)}"</{tag}>
            </div>'''
    if phd_completed:
        return "", entry
    else:
        return entry, ""


def regenerate_html():
    all_members = list_members()
    members_count = len(all_members)
    # group.html
    members_cards = []
    alumni_cards = []
    for f, d in all_members:
        card = generate_card_html(d, f)
        if d.get("alumni", False):
            alumni_cards.append(card)
        else:
            members_cards.append(card)
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        group_content = f.read()
    member_pattern = r'(<!-- MEMBER_CARDS_START -->).*?(<!-- MEMBER_CARDS_END -->)'
    member_replacement = r'\1\n' + '\n'.join(members_cards) + '\n      \\2'
    if re.search(member_pattern, group_content, re.DOTALL):
        group_content = re.sub(member_pattern, member_replacement, group_content, flags=re.DOTALL)
    else:
        raise ValueError("Could not find MEMBER_CARDS markers in group.html")
    alumni_pattern = r'(<!-- ALUMNI_CARDS_START -->).*?(<!-- ALUMNI_CARDS_END -->)'
    alumni_replacement = r'\1\n' + '\n'.join(alumni_cards) + '\n      \\2'
    if re.search(alumni_pattern, group_content, re.DOTALL):
        group_content = re.sub(alumni_pattern, alumni_replacement, group_content, flags=re.DOTALL)
    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(group_content)
    # theses.html
    ongoing_entries = []
    completed_entries = []
    for f, d in all_members:
        ongoing, completed = generate_thesis_entry_html(d)
        if ongoing:
            ongoing_entries.append(ongoing)
        if completed:
            completed_entries.append(completed)
    with open(THESES_FILE, 'r', encoding='utf-8') as f:
        theses_content = f.read()
    ongoing_pattern = r'(<!-- THESES_ONGOING_START -->).*?(<!-- THESES_ONGOING_END -->)'
    ongoing_replacement = r'\1\n' + ''.join(ongoing_entries) + '\n      \\2'
    if re.search(ongoing_pattern, theses_content, re.DOTALL):
        theses_content = re.sub(ongoing_pattern, ongoing_replacement, theses_content, flags=re.DOTALL)
    else:
        raise ValueError("Could not find THESES_ONGOING markers in theses.html")
    completed_pattern = r'(<!-- THESES_COMPLETED_START -->).*?(<!-- THESES_COMPLETED_END -->)'
    completed_replacement = r'\1\n' + ''.join(completed_entries) + '\n      \\2'
    if re.search(completed_pattern, theses_content, re.DOTALL):
        theses_content = re.sub(completed_pattern, completed_replacement, theses_content, flags=re.DOTALL)
    else:
        raise ValueError("Could not find THESES_COMPLETED markers in theses.html")
    with open(THESES_FILE, 'w', encoding='utf-8') as f:
        f.write(theses_content)
    return members_count


class ManageMembersGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manage Group Members")
        self.setMinimumSize(640, 840)
        self.resize(640, 840)
        self.selected_photo_path = ""
        self.editing_filename = None

        os.makedirs(MEMBERS_DIR, exist_ok=True)
        os.makedirs(PHOTOS_DIR, exist_ok=True)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        main_layout.addWidget(scroll)

        scroll_content = QWidget()
        scroll.setWidget(scroll_content)
        inner_layout = QVBoxLayout(scroll_content)

        # --- Member List ---
        list_group = QGroupBox("Existing Members")
        inner_layout.addWidget(list_group)
        list_vlay = QVBoxLayout(list_group)

        list_btn_row = QHBoxLayout()
        list_vlay.addLayout(list_btn_row)
        self.btn_add = QPushButton("Add New")
        self.btn_add.clicked.connect(self.add_member)
        list_btn_row.addWidget(self.btn_add)
        self.btn_edit = QPushButton("Edit Selected")
        self.btn_edit.clicked.connect(self.edit_member)
        list_btn_row.addWidget(self.btn_edit)
        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.clicked.connect(self.delete_member)
        list_btn_row.addWidget(self.btn_delete)

        self.listbox = QListWidget()
        self.listbox.setMinimumHeight(150)
        self.listbox.itemClicked.connect(self.on_list_select)
        list_vlay.addWidget(self.listbox)

        # --- Member Details ---
        det_group = QGroupBox("Member Details")
        inner_layout.addWidget(det_group)
        det_grid = QGridLayout(det_group)

        # Row 0: Title
        det_grid.addWidget(QLabel("Title:"), 0, 0, Qt.AlignmentFlag.AlignRight)
        self.title_combo = QComboBox()
        self.title_combo.addItems(["", "Dr.", "Prof.", "Mr.", "Ms."])
        self.title_combo.setCurrentIndex(0)
        self.title_combo.setMinimumWidth(200)
        det_grid.addWidget(self.title_combo, 0, 1)

        # Row 1: Given Name
        det_grid.addWidget(QLabel("Given Name: *"), 1, 0, Qt.AlignmentFlag.AlignRight)
        self.given_entry = QLineEdit()
        self.given_entry.setMinimumWidth(200)
        det_grid.addWidget(self.given_entry, 1, 1)

        # Row 2: Middle Name
        det_grid.addWidget(QLabel("Middle Name:"), 2, 0, Qt.AlignmentFlag.AlignRight)
        self.middle_entry = QLineEdit()
        self.middle_entry.setMinimumWidth(200)
        det_grid.addWidget(self.middle_entry, 2, 1)

        # Row 3: Last Name
        det_grid.addWidget(QLabel("Last Name: *"), 3, 0, Qt.AlignmentFlag.AlignRight)
        self.last_entry = QLineEdit()
        self.last_entry.setMinimumWidth(200)
        det_grid.addWidget(self.last_entry, 3, 1)

        # Row 4: Role
        det_grid.addWidget(QLabel("Role: *"), 4, 0, Qt.AlignmentFlag.AlignRight)
        self.role_combo = QComboBox()
        self.role_combo.addItems(ROLE_OPTIONS)
        self.role_combo.setCurrentIndex(0)
        self.role_combo.setMinimumWidth(200)
        det_grid.addWidget(self.role_combo, 4, 1)

        # Row 5: Alumni
        det_grid.addWidget(QLabel("Status:"), 5, 0, Qt.AlignmentFlag.AlignRight)
        self.alumni_cb = QCheckBox("Alumni?")
        det_grid.addWidget(self.alumni_cb, 5, 1)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        det_grid.addWidget(sep, 6, 0, 1, 2)

        # Row 7: Email
        det_grid.addWidget(QLabel("Email:"), 7, 0, Qt.AlignmentFlag.AlignRight)
        self.email_entry = QLineEdit()
        self.email_entry.setMinimumWidth(200)
        det_grid.addWidget(self.email_entry, 7, 1)

        # Row 8: Training 1
        det_grid.addWidget(QLabel("Training Line 1:"), 8, 0, Qt.AlignmentFlag.AlignRight)
        self.master_entry = QLineEdit()
        self.master_entry.setMinimumWidth(200)
        det_grid.addWidget(self.master_entry, 8, 1)

        # Row 9: Training 2
        det_grid.addWidget(QLabel("Training Line 2:"), 9, 0, Qt.AlignmentFlag.AlignRight)
        self.phd_entry = QLineEdit()
        self.phd_entry.setMinimumWidth(200)
        det_grid.addWidget(self.phd_entry, 9, 1)

        # Row 10: Project
        det_grid.addWidget(QLabel("Current Project:"), 10, 0, Qt.AlignmentFlag.AlignRight)
        self.project_text = QTextEdit()
        self.project_text.setMinimumWidth(200)
        self.project_text.setMaximumHeight(80)
        det_grid.addWidget(self.project_text, 10, 1)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        det_grid.addWidget(sep2, 11, 0, 1, 2)

        # Row 12: Photo
        det_grid.addWidget(QLabel("Photo:"), 12, 0, Qt.AlignmentFlag.AlignRight)
        photo_widget = QWidget()
        photo_hbox = QHBoxLayout(photo_widget)
        photo_hbox.setContentsMargins(0, 0, 0, 0)
        self.btn_select_photo = QPushButton("Select Photo...")
        self.btn_select_photo.clicked.connect(self.select_photo)
        photo_hbox.addWidget(self.btn_select_photo)
        self.photo_label = QLabel("No photo selected")
        self.photo_label.setStyleSheet("color: gray; font-size: 11px;")
        photo_hbox.addWidget(self.photo_label)
        det_grid.addWidget(photo_widget, 12, 1)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setFrameShadow(QFrame.Shadow.Sunken)
        det_grid.addWidget(sep3, 13, 0, 1, 2)

        # Row 14: Thesis Title
        det_grid.addWidget(QLabel("PhD Title:"), 14, 0, Qt.AlignmentFlag.AlignRight)
        self.thesis_title_entry = QLineEdit()
        self.thesis_title_entry.setMinimumWidth(200)
        det_grid.addWidget(self.thesis_title_entry, 14, 1)

        # Row 15: Thesis Link
        det_grid.addWidget(QLabel("Thesis Link:"), 15, 0, Qt.AlignmentFlag.AlignRight)
        self.thesis_link_entry = QLineEdit()
        self.thesis_link_entry.setMinimumWidth(200)
        det_grid.addWidget(self.thesis_link_entry, 15, 1)

        # Row 16: PhD Completed
        det_grid.addWidget(QLabel("PhD Completed?"), 16, 0, Qt.AlignmentFlag.AlignRight)
        self.phd_completed_cb = QCheckBox("Yes")
        det_grid.addWidget(self.phd_completed_cb, 16, 1)

        # Buttons
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save Member")
        self.save_btn.clicked.connect(self.save_member)
        btn_row.addWidget(self.save_btn)
        self.clear_btn = QPushButton("Clear Form")
        self.clear_btn.clicked.connect(self.clear_form)
        btn_row.addWidget(self.clear_btn)
        det_grid.addLayout(btn_row, 17, 0, 1, 2)

        # --- Generate ---
        gen_group = QGroupBox("Generate Webpage")
        inner_layout.addWidget(gen_group)
        gen_vlay = QVBoxLayout(gen_group)

        self.gen_status = QLabel("")
        gen_vlay.addWidget(self.gen_status)

        self.gen_btn = QPushButton("Generate group.html & theses.html")
        self.gen_btn.clicked.connect(self.generate_page)
        gen_vlay.addWidget(self.gen_btn)

        self.refresh_list()

    def refresh_list(self):
        self.listbox.clear()
        self.members = list_members()
        for f, d in self.members:
            name = format_name(d)
            role = d.get("role", "")
            alumni = " [Alumni]" if d.get("alumni", False) else ""
            padded_role = role[:22].ljust(22)
            display = f"  {padded_role}  {name}{alumni}"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.listbox.addItem(item)

    def on_list_select(self, item):
        fname = item.data(Qt.ItemDataRole.UserRole)
        for f, d in self.members:
            if f == fname:
                self.load_member_to_form(f, d)
                break

    def load_member_to_form(self, filename, data):
        self.editing_filename = filename
        title = data.get("title", "")
        if title in ["", "Dr.", "Prof.", "Mr.", "Ms."]:
            self.title_combo.setCurrentText(title)
        else:
            self.title_combo.setCurrentText("")

        self.given_entry.setText(data.get("given", ""))
        self.middle_entry.setText(data.get("middle", ""))
        self.last_entry.setText(data.get("last", ""))

        role = data.get("role", "")
        if role in ROLE_OPTIONS:
            self.role_combo.setCurrentText(role)
        else:
            self.role_combo.setCurrentIndex(0)

        self.alumni_cb.setChecked(data.get("alumni", False))
        self.email_entry.setText(data.get("email", ""))
        self.master_entry.setText(data.get("master", ""))
        self.phd_entry.setText(data.get("phd", ""))
        self.project_text.setPlainText(data.get("project", ""))

        photo = data.get("photo", "")
        if photo:
            abs_photo = os.path.join(BASE_DIR, photo)
            if os.path.exists(abs_photo):
                self.selected_photo_path = abs_photo
                self.photo_label.setText(os.path.basename(photo))
            else:
                self.selected_photo_path = ""
                self.photo_label.setText("Photo file missing")
        else:
            self.selected_photo_path = ""
            self.photo_label.setText("No photo selected")

        self.thesis_title_entry.setText(data.get("thesis_title", ""))
        self.thesis_link_entry.setText(data.get("thesis_link", ""))
        self.phd_completed_cb.setChecked(data.get("phd_completed", False))

    def add_member(self):
        self.editing_filename = None
        self.clear_form()
        self.given_entry.setFocus()

    def edit_member(self):
        sel = self.listbox.currentRow()
        if sel < 0:
            QMessageBox.information(self, "No Selection", "Select a member to edit.")
            return
        filename, data = self.members[sel]
        self.load_member_to_form(filename, data)

    def delete_member(self):
        sel = self.listbox.currentRow()
        if sel < 0:
            QMessageBox.information(self, "No Selection", "Select a member to delete.")
            return
        filename, data = self.members[sel]
        name = format_name(data)
        reply = QMessageBox.question(
            self, "Confirm Delete", f'Delete member "{name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            delete_member_file(filename)
            self.refresh_list()
            self.clear_form()
            QMessageBox.information(self, "Deleted", f'"{name}" deleted.')
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete: {e}")

    def select_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Photo", "",
            "Image files (*.jpg *.jpeg *.png *.gif *.webp);;All files (*.*)"
        )
        if file_path:
            self.selected_photo_path = file_path
            self.photo_label.setText(os.path.basename(file_path))

    def save_member(self):
        title = self.title_combo.currentText().strip()
        given = self.given_entry.text().strip()
        middle = self.middle_entry.text().strip()
        last = self.last_entry.text().strip()
        role = self.role_combo.currentText().strip()
        email = self.email_entry.text().strip()
        master = self.master_entry.text().strip()
        phd_data = self.phd_entry.text().strip()
        project = self.project_text.toPlainText().strip()
        thesis_title = self.thesis_title_entry.text().strip()
        thesis_link = self.thesis_link_entry.text().strip()

        if not given or not last or not role:
            QMessageBox.warning(self, "Validation",
                                 "Given Name, Last Name, and Role are required.")
            return

        if self.editing_filename:
            filename = self.editing_filename
        else:
            name = f"{given} {last}"
            slug = slugify(name)
            filename = f"{slug}.json"
            if os.path.exists(os.path.join(MEMBERS_DIR, filename)):
                i = 1
                while os.path.exists(os.path.join(MEMBERS_DIR, f"{slug}_{i}.json")):
                    i += 1
                filename = f"{slug}_{i}.json"

        old_photo = ""
        if self.editing_filename:
            try:
                old_data = load_member(self.editing_filename)
                old_photo = old_data.get("photo", "")
            except:
                pass

        photo_web_path = old_photo if old_photo else ""
        if self.selected_photo_path and self.photo_label.text() != "Photo file missing":
            abs_selected = os.path.abspath(self.selected_photo_path)
            ext = os.path.splitext(self.selected_photo_path)[1].lower()
            name = f"{given} {last}"
            safe_name = slugify(name)
            new_photo_name = safe_name + ext
            dest_path = os.path.join(PHOTOS_DIR, new_photo_name)
            if abs_selected != os.path.abspath(dest_path):
                try:
                    os.makedirs(PHOTOS_DIR, exist_ok=True)
                    shutil.copy(self.selected_photo_path, dest_path)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to copy photo: {e}")
                    return
            photo_web_path = f"assets/group/{new_photo_name}"

        data = {
            "title": title,
            "given": given,
            "middle": middle,
            "last": last,
            "role": role,
            "alumni": self.alumni_cb.isChecked(),
            "email": email,
            "master": master,
            "phd": phd_data,
            "project": project,
            "photo": photo_web_path,
            "thesis_title": thesis_title,
            "thesis_link": thesis_link,
            "phd_completed": self.phd_completed_cb.isChecked(),
        }

        try:
            save_member(filename, data)
            self.editing_filename = filename
            self.refresh_list()
            QMessageBox.information(self, "Saved",
                                     f'"{format_name(data)}" saved.')
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def clear_form(self):
        self.title_combo.setCurrentText("")
        self.given_entry.clear()
        self.middle_entry.clear()
        self.last_entry.clear()
        self.role_combo.setCurrentIndex(0)
        self.alumni_cb.setChecked(False)
        self.email_entry.clear()
        self.master_entry.clear()
        self.phd_entry.clear()
        self.project_text.clear()
        self.selected_photo_path = ""
        self.photo_label.setText("No photo selected")
        self.thesis_title_entry.clear()
        self.thesis_link_entry.clear()
        self.phd_completed_cb.setChecked(False)
        self.editing_filename = None

    def generate_page(self):
        try:
            count = regenerate_html()
            git_msg = ""
            try:
                subprocess.run(
                    ["git", "add", HTML_FILE, THESES_FILE, PHOTOS_DIR],
                    check=True, cwd=BASE_DIR, capture_output=True, text=True
                )
                subprocess.run(
                    ["git", "commit", "-m", f"Update group members page ({count} members)"],
                    check=True, cwd=BASE_DIR, capture_output=True, text=True
                )
                subprocess.run(
                    ["git", "push"],
                    check=True, cwd=BASE_DIR, capture_output=True, text=True
                )
                git_msg = " (committed and pushed to Git)"
            except Exception as e:
                git_msg = f" (Git: {e})"

            self.gen_status.setText(f"OK \u2014 {count} member(s){git_msg}")
            self.gen_status.setStyleSheet("color: green;")
            QMessageBox.information(
                self, "Success",
                f"Generated group.html and theses.html with {count} member(s).{git_msg}"
            )
        except Exception as e:
            self.gen_status.setText(f"Error: {e}")
            self.gen_status.setStyleSheet("color: red;")
            QMessageBox.critical(self, "Error", f"Failed to generate page: {e}")


if __name__ == "__main__":
    if not os.path.exists(HTML_FILE):
        print(f"Error: {HTML_FILE} not found.")
    else:
        app = QApplication(sys.argv)
        window = ManageMembersGUI()
        window.show()
        sys.exit(app.exec())