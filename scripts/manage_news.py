"""
Manage News — PyQt6 GUI editor for news items.
Generates news.html from JSON data in assets/news/.
"""

import sys
import os
import re
import json
import shutil
import subprocess
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFormLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QComboBox, QSpinBox, QCheckBox, QListWidget,
    QListWidgetItem, QScrollArea, QGroupBox, QFrame, QMessageBox,
    QFileDialog, QSizePolicy
)
from PyQt6.QtCore import Qt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_FILE = os.path.join(BASE_DIR, "news.html")
NEWS_DIR = os.path.join(BASE_DIR, "assets", "news")

MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def slugify(text):
    s = text.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s[:50] or "news"


def format_display_date(date_str):
    try:
        parts = date_str.split("-")
        if len(parts) == 3:
            y, m, d = parts
            month_name = MONTHS[int(m)]
            return f"{int(d)} {month_name} {y}"
        elif len(parts) == 2:
            y, m = parts
            month_name = MONTHS[int(m)]
            return f"{month_name} {y}"
    except (ValueError, IndexError):
        pass
    return date_str


def load_news(filename):
    with open(os.path.join(NEWS_DIR, filename), 'r', encoding='utf-8') as f:
        return json.load(f)


def save_news(filename, data):
    with open(os.path.join(NEWS_DIR, filename), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def delete_news_file(filename):
    path = os.path.join(NEWS_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
    base = os.path.splitext(path)[0]
    for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
        associated = base + ext
        if os.path.exists(associated):
            os.remove(associated)
    try:
        data = load_news(filename)
        old_image = data.get("image", "")
        if old_image:
            img_path = os.path.join(BASE_DIR, old_image)
            if os.path.exists(img_path):
                os.remove(img_path)
    except:
        pass


def list_news():
    os.makedirs(NEWS_DIR, exist_ok=True)
    files = sorted([f for f in os.listdir(NEWS_DIR) if f.endswith('.json')])
    items = []
    for f in files:
        try:
            data = load_news(f)
            items.append((f, data))
        except:
            items.append((f, {"title": "[error]", "date": "0000-00-00"}))
    items.sort(key=lambda x: (x[1].get("date", "0000-00-00"), x[0]), reverse=True)
    return items


def escape_html(text):
    text = str(text)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&#39;")
    return text


def generate_item_html(data, filename):
    title = escape_html(data.get("title", ""))
    excerpt = escape_html(data.get("excerpt", ""))
    date_str = data.get("date", "")
    image = data.get("image", "")
    display_date = format_display_date(date_str)
    cls = "has-image" if image else ""
    lines = []
    lines.append(f'        <!-- NEWS START: {filename} -->')
    item_id = filename.replace(".json", "")
    lines.append(f'        <div class="blog-item {cls}" id="news-{item_id}" data-news="{filename}">')
    lines.append(f'          <div class="blog-date">{display_date}</div>')
    lines.append(f'          <div class="blog-body">')
    lines.append(f'            <div class="blog-title">{title}</div>')
    lines.append(f'            <div class="blog-excerpt">{excerpt}</div>')
    lines.append(f'          </div>')
    if image:
        web_path = image.replace("\\", "/")
        lines.append(f'          <img src="{web_path}" alt="{title}" class="blog-image" loading="lazy">')
    lines.append(f'        </div>')
    lines.append(f'        <!-- NEWS END: {filename} -->')
    return "\n".join(lines)


def regenerate_html():
    all_news = list_news()
    items_html = "\n".join(generate_item_html(d, f) for f, d in all_news)
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    pattern = r'(<!-- NEWS_START -->).*?(<!-- NEWS_END -->)'
    replacement = r'\1\n' + items_html + '\n      \\2'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    else:
        raise ValueError("Could not find NEWS_START/NEWS_END markers in news.html")
    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    return len(all_news)


class ManageNewsGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manage News")
        self.setMinimumSize(480, 400)
        self.resize(640, 780)
        self.selected_image_path = ""
        self.editing_filename = None

        os.makedirs(NEWS_DIR, exist_ok=True)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- Scrollable area ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        layout.addWidget(scroll, 1)

        scroll_content = QWidget()
        scroll.setWidget(scroll_content)
        self.scroll_layout = QVBoxLayout(scroll_content)

        # --- News List ---
        list_group = QGroupBox("Existing News Items")
        self.scroll_layout.addWidget(list_group)
        list_vlay = QVBoxLayout(list_group)

        list_btn_row = QHBoxLayout()
        list_vlay.addLayout(list_btn_row)
        self.btn_add = QPushButton("Add New")
        self.btn_add.clicked.connect(self.add_news)
        list_btn_row.addWidget(self.btn_add)
        self.btn_edit = QPushButton("Edit Selected")
        self.btn_edit.clicked.connect(self.edit_news)
        list_btn_row.addWidget(self.btn_edit)
        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.clicked.connect(self.delete_news)
        list_btn_row.addWidget(self.btn_delete)

        self.listbox = QListWidget()
        self.listbox.setMinimumHeight(150)
        self.listbox.itemClicked.connect(self.on_list_select)
        list_vlay.addWidget(self.listbox)

        # --- News Details ---
        det_group = QGroupBox("News Details")
        self.scroll_layout.addWidget(det_group)
        det_grid = QGridLayout(det_group)

        # Row 0: Title
        det_grid.addWidget(QLabel("Title: *"), 0, 0, Qt.AlignmentFlag.AlignRight)
        self.title_entry = QLineEdit()
        self.title_entry.setMinimumWidth(300)
        det_grid.addWidget(self.title_entry, 0, 1)

        # Row 1: Date
        det_grid.addWidget(QLabel("Date: *"), 1, 0, Qt.AlignmentFlag.AlignRight)
        date_widget = QWidget()
        date_hlay = QHBoxLayout(date_widget)
        date_hlay.setContentsMargins(0, 0, 0, 0)
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2020, 2100)
        self.year_spin.setValue(datetime.now().year)
        date_hlay.addWidget(self.year_spin)
        date_hlay.addWidget(QLabel("-"))
        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 12)
        self.month_spin.setValue(datetime.now().month)
        date_hlay.addWidget(self.month_spin)
        date_hlay.addWidget(QLabel("-"))
        self.day_spin = QSpinBox()
        self.day_spin.setRange(1, 31)
        self.day_spin.setValue(datetime.now().day)
        date_hlay.addWidget(self.day_spin)
        date_hlay.addWidget(QLabel("  (YYYY-MM-DD)"))
        det_grid.addWidget(date_widget, 1, 1)

        # Row 2: Excerpt
        det_grid.addWidget(QLabel("Excerpt:"), 2, 0, Qt.AlignmentFlag.AlignRight)
        self.excerpt_text = QTextEdit()
        self.excerpt_text.setMinimumWidth(300)
        self.excerpt_text.setMaximumHeight(120)
        det_grid.addWidget(self.excerpt_text, 2, 1)

        # Row 3: Image
        det_grid.addWidget(QLabel("Image:"), 3, 0, Qt.AlignmentFlag.AlignRight)
        img_widget = QWidget()
        img_hlay = QHBoxLayout(img_widget)
        img_hlay.setContentsMargins(0, 0, 0, 0)
        self.btn_select_image = QPushButton("Select Image...")
        self.btn_select_image.clicked.connect(self.select_image)
        img_hlay.addWidget(self.btn_select_image)
        self.image_label = QLabel("No image selected")
        self.image_label.setStyleSheet("color: gray; font-size: 11px;")
        img_hlay.addWidget(self.image_label)
        det_grid.addWidget(img_widget, 3, 1)

        # Row 4: Buttons
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save News")
        self.save_btn.clicked.connect(self.save_news)
        btn_row.addWidget(self.save_btn)
        self.clear_btn = QPushButton("Clear Form")
        self.clear_btn.clicked.connect(self.clear_form)
        btn_row.addWidget(self.clear_btn)
        det_grid.addLayout(btn_row, 4, 0, 1, 2)

        # --- Generate ---
        gen_group = QGroupBox("Generate Webpage")
        self.scroll_layout.addWidget(gen_group)
        gen_vlay = QVBoxLayout(gen_group)

        self.gen_status = QLabel("")
        gen_vlay.addWidget(self.gen_status)

        self.gen_btn = QPushButton("Generate news.html")
        self.gen_btn.clicked.connect(self.generate_page)
        gen_vlay.addWidget(self.gen_btn)

        self.refresh_list()

    def refresh_list(self):
        self.listbox.clear()
        self.news_items = list_news()
        for f, d in self.news_items:
            title = d.get("title", "[error]")
            date_str = d.get("date", "")
            display = format_display_date(date_str)
            padded_date = (display[:18].ljust(18))
            item = QListWidgetItem(f"  {padded_date}  {title}")
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.listbox.addItem(item)

    def on_list_select(self, item):
        fname = item.data(Qt.ItemDataRole.UserRole)
        for f, d in self.news_items:
            if f == fname:
                self.load_news_to_form(f, d)
                break

    def load_news_to_form(self, filename, data):
        self.editing_filename = filename
        self.title_entry.setText(data.get("title", ""))
        date_str = data.get("date", "")
        parts = date_str.split("-")
        if len(parts) == 3:
            self.year_spin.setValue(int(parts[0]))
            self.month_spin.setValue(int(parts[1]))
            self.day_spin.setValue(int(parts[2]))
        elif len(parts) == 2:
            self.year_spin.setValue(int(parts[0]))
            self.month_spin.setValue(int(parts[1]))
        self.excerpt_text.setPlainText(data.get("excerpt", ""))

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

    def add_news(self):
        self.editing_filename = None
        self.clear_form()
        self.title_entry.setFocus()

    def edit_news(self):
        sel = self.listbox.currentRow()
        if sel < 0:
            QMessageBox.information(self, "No Selection", "Select a news item to edit.")
            return
        filename, data = self.news_items[sel]
        self.load_news_to_form(filename, data)

    def delete_news(self):
        sel = self.listbox.currentRow()
        if sel < 0:
            QMessageBox.information(self, "No Selection", "Select a news item to delete.")
            return
        filename, data = self.news_items[sel]
        title = data.get("title", filename)
        reply = QMessageBox.question(
            self, "Confirm Delete", f'Delete news item "{title}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            delete_news_file(filename)
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

    def save_news(self):
        title = self.title_entry.text().strip()
        year = self.year_spin.value()
        month = self.month_spin.value()
        day = self.day_spin.value()
        excerpt = self.excerpt_text.toPlainText().strip()

        if not title:
            QMessageBox.warning(self, "Validation", "Title is required.")
            return

        if not (1 <= month <= 12 and 1 <= day <= 31):
            QMessageBox.warning(self, "Validation", "Invalid date. Use YYYY-MM-DD.")
            return

        date_str = f"{year:04d}-{month:02d}-{day:02d}"

        if self.editing_filename:
            filename = self.editing_filename
        else:
            slug = slugify(title)
            filename = f"{slug}.json"
            if os.path.exists(os.path.join(NEWS_DIR, filename)):
                i = 1
                while os.path.exists(os.path.join(NEWS_DIR, f"{slug}_{i}.json")):
                    i += 1
                filename = f"{slug}_{i}.json"

        old_image = ""
        if self.editing_filename:
            try:
                old_data = load_news(self.editing_filename)
                old_image = old_data.get("image", "")
            except:
                pass

        image_web_path = old_image if old_image else ""
        if self.selected_image_path and self.image_label.text() != "Image file missing":
            abs_selected = os.path.abspath(self.selected_image_path)
            ext = os.path.splitext(self.selected_image_path)[1].lower()
            new_img_name = slugify(title) + ext
            dest_path = os.path.join(NEWS_DIR, new_img_name)
            if abs_selected != os.path.abspath(dest_path):
                try:
                    shutil.copy(self.selected_image_path, dest_path)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to copy image: {e}")
                    return
            image_web_path = f"assets/news/{new_img_name}"

        data = {
            "title": title,
            "date": date_str,
            "excerpt": excerpt,
            "image": image_web_path
        }

        try:
            save_news(filename, data)
            self.editing_filename = filename
            self.refresh_list()
            QMessageBox.information(self, "Saved", f'"{title}" saved.')
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def clear_form(self):
        self.title_entry.clear()
        self.year_spin.setValue(datetime.now().year)
        self.month_spin.setValue(datetime.now().month)
        self.day_spin.setValue(datetime.now().day)
        self.excerpt_text.clear()
        self.selected_image_path = ""
        self.image_label.setText("No image selected")
        self.editing_filename = None

    def generate_page(self):
        try:
            count = regenerate_html()
            git_msg = ""
            try:
                subprocess.run(
                    ["git", "add", HTML_FILE, NEWS_DIR],
                    check=True, cwd=BASE_DIR, capture_output=True, text=True, timeout=30
                )
                subprocess.run(
                    ["git", "commit", "-m", f"Update news page ({count} items)"],
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

            self.gen_status.setText(f"OK \u2014 {count} news item(s){git_msg}")
            self.gen_status.setStyleSheet("color: green;")
            QMessageBox.information(self, "Success",
                                     f"Generated news.html with {count} item(s).{git_msg}")
        except Exception as e:
            self.gen_status.setText(f"Error: {e}")
            self.gen_status.setStyleSheet("color: red;")
            QMessageBox.critical(self, "Error", f"Failed to generate page: {e}")


if __name__ == "__main__":
    if not os.path.exists(HTML_FILE):
        print(f"Error: {HTML_FILE} not found.")
    else:
        app = QApplication(sys.argv)
        window = ManageNewsGUI()
        window.show()
        sys.exit(app.exec())