"""
Manage Open Positions — PyQt6 GUI editor for position items.
Generates positions.html from JSON data in assets/positions/.
"""

import sys
import os
import re
import json
import shutil
import subprocess
from datetime import datetime, date
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QTextEdit, QPushButton,
    QComboBox, QCheckBox, QListWidget, QListWidgetItem, QScrollArea,
    QGroupBox, QFrame, QMessageBox, QFileDialog, QSizePolicy,
    QSpinBox
)
from PyQt6.QtCore import Qt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_FILE = os.path.join(BASE_DIR, "positions.html")
POSITIONS_DIR = os.path.join(BASE_DIR, "assets", "positions")

STATUS_OPTIONS = ["Bachelor internship", "Master internship", "PhD", "Postdoc", "Other", "Custom"]


def slugify(text):
    s = text.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s[:50] or "position"


def load_position(filename):
    with open(os.path.join(POSITIONS_DIR, filename), 'r', encoding='utf-8') as f:
        return json.load(f)


def save_position(filename, data):
    with open(os.path.join(POSITIONS_DIR, filename), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def delete_position_file(filename):
    path = os.path.join(POSITIONS_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
    base = os.path.splitext(path)[0]
    for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf', '.doc', '.docx']:
        associated = base + ext
        if os.path.exists(associated):
            os.remove(associated)


def list_positions():
    os.makedirs(POSITIONS_DIR, exist_ok=True)
    files = sorted([f for f in os.listdir(POSITIONS_DIR) if f.endswith('.json')])
    result = []
    for f in files:
        try:
            data = load_position(f)
            result.append((f, data))
        except:
            result.append((f, {"title": f"[error reading file]", "status": ""}))
    return result


def is_active(data, today=None):
    if not data.get("public", False):
        return False
    created = data.get("created_at", "")
    limit = data.get("day_limit", 0)
    if not created or limit == 0:
        return True
    if today is None:
        today = date.today()
    try:
        c = datetime.strptime(created, "%Y-%m-%d").date()
        return (today - c).days <= limit
    except ValueError:
        return True


def escape_html(text):
    text = str(text)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&#39;")
    return text


STATUS_COLORS = {
    "Bachelor internship": ("#e8f5e9", "#2e7d32"),
    "Master internship": ("#e3f2fd", "#1565c0"),
    "PhD": ("#fce4ec", "#c62828"),
    "Postdoc": ("#fff3e0", "#e65100"),
    "Other": ("#f3e5f5", "#6a1b9a"),
    "Custom": ("#f0f0f0", "#555555"),
}

DEFAULT_BG = "#f0f0f0"
DEFAULT_FG = "#333333"


def generate_card_html(data, filename):
    title = escape_html(data.get("title", ""))
    status = escape_html(data.get("status", ""))
    desc = escape_html(data.get("description", ""))
    image = data.get("image", "")
    attachment = data.get("attachment", "")
    created = data.get("created_at", "")
    limit = data.get("day_limit", 0)
    bg, fg = STATUS_COLORS.get(data.get("status", ""), (DEFAULT_BG, DEFAULT_FG))
    lines = []
    lines.append(f'        <!-- POSITION START: {filename} -->')
    lines.append(f'        <div class="position-card" data-pos="{filename}" data-created="{created}" data-limit="{limit}">')
    lines.append(f'          <div class="position-card-body">')
    lines.append(f'            <span class="position-badge" style="background:{bg};color:{fg}">{status}</span>')
    lines.append(f'            <h3>{title}</h3>')
    if created:
        lines.append(f'            <p class="position-date">Added: {created}</p>')
    if desc:
        lines.append(f'            <p class="position-preview">{desc}</p>')
    lines.append(f'          </div>')
    if image:
        web_path = image.replace("\\", "/")
        lines.append(f'          <img src="{web_path}" alt="{title}" class="position-thumb" loading="lazy">')
    lines.append(f'          <div class="position-details" style="display:none">')
    lines.append(f'            <p class="detail-description">{desc}</p>')
    if image:
        lines.append(f'            <p class="detail-image">{web_path}</p>')
    else:
        lines.append(f'            <p class="detail-image"></p>')
    if attachment:
        att_path = attachment.replace("\\", "/")
        lines.append(f'            <p class="detail-attachment">{att_path}</p>')
    else:
        lines.append(f'            <p class="detail-attachment"></p>')
    lines.append(f'          </div>')
    lines.append(f'        </div>')
    lines.append(f'        <!-- POSITION END: {filename} -->')
    return "\n".join(lines)


def regenerate_html(html_file, positions_dir):
    all_pos = list_positions()
    active = [(f, d) for f, d in all_pos if is_active(d)]
    cards = "\n".join(generate_card_html(d, f) for f, d in active)
    placeholder = '''      <div class="position-card">
        <h3>No specific open positions at the moment</h3>
        <p>Spontaneous applications are always welcome.</p>
      </div>'''
    if not cards:
        cards = placeholder
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    pattern = r'(<p style="margin-bottom: 2rem; text-align: justify; color: var\(--muted\);">.*?</p>\s*)(.*?)(\s*</section>)'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        raise ValueError(
            "Could not find positions section pattern in HTML. "
            "Has the intro <p> changed?"
        )
    new_content = (
        content[:match.start()] +
        match.group(1) + cards + "\n      " + match.group(3) +
        content[match.end():]
    )
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return len(active)


class ManagePositionsGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manage Open Positions")
        self.setMinimumSize(480, 400)
        self.resize(640, 840)
        self.selected_image_path = ""
        self.selected_attachment_path = ""
        self.editing_filename = None

        os.makedirs(POSITIONS_DIR, exist_ok=True)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        layout.addWidget(scroll, 1)

        scroll_content = QWidget()
        scroll.setWidget(scroll_content)
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(10, 10, 10, 10)

        # --- Position List ---
        list_group = QGroupBox("Existing Positions")
        content_layout.addWidget(list_group)
        list_vlay = QVBoxLayout(list_group)

        list_btn_row = QHBoxLayout()
        list_vlay.addLayout(list_btn_row)
        self.btn_add = QPushButton("Add New")
        self.btn_add.clicked.connect(self.add_position)
        list_btn_row.addWidget(self.btn_add)
        self.btn_edit = QPushButton("Edit Selected")
        self.btn_edit.clicked.connect(self.edit_position)
        list_btn_row.addWidget(self.btn_edit)
        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.clicked.connect(self.delete_position)
        list_btn_row.addWidget(self.btn_delete)

        self.listbox = QListWidget()
        self.listbox.setMinimumHeight(150)
        list_vlay.addWidget(self.listbox)

        # --- Position Details ---
        det_group = QGroupBox("Position Details")
        content_layout.addWidget(det_group, stretch=1)
        det_grid = QGridLayout(det_group)

        # Row 0: Title
        det_grid.addWidget(QLabel("Title:"), 0, 0, Qt.AlignmentFlag.AlignRight)
        self.title_entry = QLineEdit()
        self.title_entry.setMinimumWidth(280)
        det_grid.addWidget(self.title_entry, 0, 1)

        # Row 1: Status
        det_grid.addWidget(QLabel("Status:"), 1, 0, Qt.AlignmentFlag.AlignRight)
        status_widget = QWidget()
        status_hbox = QHBoxLayout(status_widget)
        status_hbox.setContentsMargins(0, 0, 0, 0)
        self.status_combo = QComboBox()
        self.status_combo.addItems(STATUS_OPTIONS)
        self.status_combo.setCurrentIndex(0)
        self.status_combo.setMinimumWidth(150)
        status_hbox.addWidget(self.status_combo)
        self.custom_status_entry = QLineEdit()
        self.custom_status_entry.setPlaceholderText("Enter custom status...")
        self.custom_status_entry.setMinimumWidth(120)
        self.custom_status_entry.hide()
        status_hbox.addWidget(self.custom_status_entry)
        det_grid.addWidget(status_widget, 1, 1)
        self.status_combo.currentIndexChanged.connect(self.on_status_changed)

        # Row 2: Description
        det_grid.addWidget(QLabel("Description:"), 2, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        self.desc_text = QTextEdit()
        self.desc_text.setMinimumWidth(280)
        self.desc_text.setMaximumHeight(120)
        det_grid.addWidget(self.desc_text, 2, 1)

        # Row 3: Image
        det_grid.addWidget(QLabel("Image:"), 3, 0, Qt.AlignmentFlag.AlignRight)
        img_widget = QWidget()
        img_hbox = QHBoxLayout(img_widget)
        img_hbox.setContentsMargins(0, 0, 0, 0)
        self.btn_select_image = QPushButton("Select Image...")
        self.btn_select_image.clicked.connect(self.select_image)
        img_hbox.addWidget(self.btn_select_image)
        self.image_label = QLabel("No image selected")
        self.image_label.setStyleSheet("color: gray; font-size: 11px;")
        img_hbox.addWidget(self.image_label)
        det_grid.addWidget(img_widget, 3, 1)

        # Row 4: Attachment
        det_grid.addWidget(QLabel("Attachment:"), 4, 0, Qt.AlignmentFlag.AlignRight)
        att_widget = QWidget()
        att_hbox = QHBoxLayout(att_widget)
        att_hbox.setContentsMargins(0, 0, 0, 0)
        self.btn_select_attachment = QPushButton("Select File...")
        self.btn_select_attachment.clicked.connect(self.select_attachment)
        att_hbox.addWidget(self.btn_select_attachment)
        self.attachment_label = QLabel("No file selected")
        self.attachment_label.setStyleSheet("color: gray; font-size: 11px;")
        att_hbox.addWidget(self.attachment_label)
        det_grid.addWidget(att_widget, 4, 1)

        # Row 5: Public
        det_grid.addWidget(QLabel("Public:"), 5, 0, Qt.AlignmentFlag.AlignRight)
        self.public_cb = QCheckBox("Show on website")
        self.public_cb.setChecked(True)
        det_grid.addWidget(self.public_cb, 5, 1)

        # Row 6: Day limit
        det_grid.addWidget(QLabel("Day limit:"), 6, 0, Qt.AlignmentFlag.AlignRight)
        lim_widget = QWidget()
        lim_hbox = QHBoxLayout(lim_widget)
        lim_hbox.setContentsMargins(0, 0, 0, 0)
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(0, 9999)
        self.limit_spin.setValue(90)
        lim_hbox.addWidget(self.limit_spin)
        lim_hbox.addWidget(QLabel("days (0 = no limit)"))
        det_grid.addWidget(lim_widget, 6, 1)

        # Buttons
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save Position")
        self.save_btn.clicked.connect(self.save_position)
        btn_row.addWidget(self.save_btn)
        self.clear_btn = QPushButton("Clear Form")
        self.clear_btn.clicked.connect(self.clear_form)
        btn_row.addWidget(self.clear_btn)
        det_grid.addLayout(btn_row, 7, 0, 1, 2)

        # --- Generate ---
        gen_group = QGroupBox("Generate Webpage")
        content_layout.addWidget(gen_group)
        gen_vlay = QVBoxLayout(gen_group)

        self.gen_status = QLabel("")
        gen_vlay.addWidget(self.gen_status)

        self.gen_btn = QPushButton("Generate positions.html")
        self.gen_btn.clicked.connect(self.generate_page)
        gen_vlay.addWidget(self.gen_btn)

        self.refresh_list()

    def refresh_list(self):
        self.listbox.clear()
        self.positions = list_positions()
        for f, d in self.positions:
            title = d.get("title", "[error]")
            status = d.get("status", "")
            active = is_active(d)
            padded_status = status[:22].ljust(22)
            display = f"  {padded_status}  {title}"
            item = QListWidgetItem(display)
            if not active:
                item.setForeground(Qt.GlobalColor.gray)
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.listbox.addItem(item)

    def add_position(self):
        self.editing_filename = None
        self.clear_form()
        self.title_entry.setFocus()

    def edit_position(self):
        sel = self.listbox.currentRow()
        if sel < 0:
            QMessageBox.information(self, "No Selection", "Select a position to edit.")
            return
        filename, data = self.positions[sel]
        self.editing_filename = filename
        self.title_entry.setText(data.get("title", ""))
        status = data.get("status", "")
        if status in STATUS_OPTIONS:
            self.status_combo.setCurrentText(status)
        else:
            self.status_combo.setCurrentText("Custom")
            self.custom_status_entry.setText(status)
            self.custom_status_entry.show()
        self.desc_text.setPlainText(data.get("description", ""))
        self.public_cb.setChecked(data.get("public", True))
        self.limit_spin.setValue(data.get("day_limit", 90))

        img = data.get("image", "")
        if img:
            abs_img = os.path.join(BASE_DIR, img)
            if os.path.exists(abs_img):
                self.selected_image_path = abs_img
                self.image_label.setText(os.path.basename(img))
            else:
                self.selected_image_path = ""
                self.image_label.setText("Image file missing")
        else:
            self.selected_image_path = ""
            self.image_label.setText("No image selected")

        att = data.get("attachment", "")
        if att:
            abs_att = os.path.join(BASE_DIR, att)
            if os.path.exists(abs_att):
                self.selected_attachment_path = abs_att
                self.attachment_label.setText(os.path.basename(att))
            else:
                self.selected_attachment_path = ""
                self.attachment_label.setText("Attachment file missing")
        else:
            self.selected_attachment_path = ""
            self.attachment_label.setText("No file selected")

    def delete_position(self):
        sel = self.listbox.currentRow()
        if sel < 0:
            QMessageBox.information(self, "No Selection", "Select a position to delete.")
            return
        filename, data = self.positions[sel]
        title = data.get("title", filename)
        reply = QMessageBox.question(
            self, "Confirm Delete", f'Delete position "{title}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            delete_position_file(filename)
            self.refresh_list()
            self.clear_form()
            QMessageBox.information(self, "Deleted", f'"{title}" deleted.')
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete: {e}")

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Image files (*.jpg *.jpeg *.png *.gif *.webp);;All files (*.*)"
        )
        if file_path:
            self.selected_image_path = file_path
            self.image_label.setText(os.path.basename(file_path))

    def select_attachment(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Attachment", "",
            "Documents (*.pdf *.doc *.docx);;All files (*.*)"
        )
        if file_path:
            self.selected_attachment_path = file_path
            self.attachment_label.setText(os.path.basename(file_path))

    def save_position(self):
        title = self.title_entry.text().strip()
        status_raw = self.status_combo.currentText().strip()
        if status_raw == "Custom":
            status = self.custom_status_entry.text().strip()
            if not status:
                QMessageBox.warning(self, "Validation", "Custom status text is required.")
                return
        else:
            status = status_raw
        description = self.desc_text.toPlainText().strip()

        if not title:
            QMessageBox.warning(self, "Validation", "Title is required.")
            return
        if not status:
            QMessageBox.warning(self, "Validation", "Status is required.")
            return

        if self.editing_filename:
            filename = self.editing_filename
        else:
            slug = slugify(title)
            filename = f"{slug}.json"
            if os.path.exists(os.path.join(POSITIONS_DIR, filename)):
                i = 1
                while os.path.exists(os.path.join(POSITIONS_DIR, f"{slug}_{i}.json")):
                    i += 1
                filename = f"{slug}_{i}.json"

        old_image = ""
        old_attachment = ""
        if self.editing_filename:
            try:
                old_data = load_position(self.editing_filename)
                old_image = old_data.get("image", "")
                old_attachment = old_data.get("attachment", "")
            except:
                pass

        image_web_path = old_image if old_image else ""
        if self.selected_image_path and self.image_label.text() != "Image file missing":
            abs_selected = os.path.abspath(self.selected_image_path)
            ext = os.path.splitext(self.selected_image_path)[1].lower()
            new_img_name = slugify(title) + ext
            dest_path = os.path.join(POSITIONS_DIR, new_img_name)
            if abs_selected != os.path.abspath(dest_path):
                try:
                    shutil.copy(self.selected_image_path, dest_path)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to copy image: {e}")
                    return
            image_web_path = f"assets/positions/{new_img_name}"

        attachment_web_path = old_attachment if old_attachment else ""
        if self.selected_attachment_path and self.attachment_label.text() != "Attachment file missing":
            abs_selected = os.path.abspath(self.selected_attachment_path)
            ext = os.path.splitext(self.selected_attachment_path)[1].lower()
            new_att_name = slugify(title) + ext
            dest_path = os.path.join(POSITIONS_DIR, new_att_name)
            if abs_selected != os.path.abspath(dest_path):
                try:
                    shutil.copy(self.selected_attachment_path, dest_path)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to copy attachment: {e}")
                    return
            attachment_web_path = f"assets/positions/{new_att_name}"

        data = {
            "title": title,
            "status": status,
            "description": description,
            "image": image_web_path,
            "attachment": attachment_web_path,
            "public": self.public_cb.isChecked(),
            "day_limit": int(self.limit_spin.value()),
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }

        if self.editing_filename:
            try:
                old_data = load_position(self.editing_filename)
                data["created_at"] = old_data.get("created_at", data["created_at"])
            except:
                pass

        try:
            save_position(filename, data)
            self.editing_filename = filename
            self.refresh_list()
            QMessageBox.information(self, "Saved", f'"{title}" saved.')
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def on_status_changed(self, index):
        is_custom = self.status_combo.currentText() == "Custom"
        self.custom_status_entry.setVisible(is_custom)
        if is_custom:
            self.custom_status_entry.setFocus()

    def clear_form(self):
        self.title_entry.clear()
        self.status_combo.setCurrentIndex(0)
        self.custom_status_entry.clear()
        self.custom_status_entry.hide()
        self.desc_text.clear()
        self.selected_image_path = ""
        self.image_label.setText("No image selected")
        self.selected_attachment_path = ""
        self.attachment_label.setText("No file selected")
        self.public_cb.setChecked(True)
        self.limit_spin.setValue(90)
        self.editing_filename = None

    def generate_page(self):
        try:
            count = regenerate_html(HTML_FILE, POSITIONS_DIR)
            git_msg = ""
            try:
                subprocess.run(
                    ["git", "add", HTML_FILE, POSITIONS_DIR],
                    check=True, cwd=BASE_DIR, capture_output=True, text=True, timeout=30
                )
                subprocess.run(
                    ["git", "commit", "-m", f"Update open positions page ({count} active)"],
                    check=True, cwd=BASE_DIR, capture_output=True, text=True, timeout=30
                )
                git_msg = " (committed)"
                try:
                    subprocess.run(
                        ["git", "push"],
                        check=True, cwd=BASE_DIR, capture_output=True, text=True, timeout=60
                    )
                    git_msg = " (committed and pushed to GitHub)"
                except Exception as e:
                    git_msg = " (committed, but push to GitHub failed)"
                    QMessageBox.warning(
                        self, "Push to GitHub Failed",
                        "The local commit succeeded, but pushing to GitHub failed.\n\n"
                        f"Error: {e}\n\n"
                        "To push manually, run in the terminal:\n"
                        "  git push"
                    )
            except Exception as e:
                git_msg = f" (Git error: {e})"

            self.gen_status.setText(f"OK \u2014 {count} active position(s){git_msg}")
            self.gen_status.setStyleSheet("color: green;")
            QMessageBox.information(
                self, "Success",
                f"Generated positions.html with {count} active position(s).{git_msg}"
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
        window = ManagePositionsGUI()
        window.show()
        sys.exit(app.exec())