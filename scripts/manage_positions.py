import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil
import os
import re
import json
import subprocess
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_FILE = os.path.join(BASE_DIR, "positions.html")
POSITIONS_DIR = os.path.join(BASE_DIR, "assets", "positions")

STATUS_OPTIONS = ["Bachelor internship", "Master internship", "PhD", "Postdoc", "Other"]


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
    # Remove associated image and attachment files
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
}

DEFAULT_BG = "#f0f0f0"
DEFAULT_FG = "#333333"


def generate_card_html(data, filename):
    title = escape_html(data.get("title", ""))
    status = escape_html(data.get("status", ""))
    desc = escape_html(data.get("description", ""))
    image = data.get("image", "")
    attachment = data.get("attachment", "")

    bg, fg = STATUS_COLORS.get(data.get("status", ""), (DEFAULT_BG, DEFAULT_FG))

    lines = []
    lines.append(f'        <!-- POSITION START: {filename} -->')
    lines.append(f'        <div class="position-card" data-pos="{filename}">')
    lines.append(f'          <span class="position-badge" style="background:{bg};color:{fg}">{status}</span>')
    if image:
        web_path = image.replace("\\", "/")
        lines.append(f'          <img src="{web_path}" alt="{title}" class="position-thumb" loading="lazy">')
    lines.append(f'          <h3>{title}</h3>')
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

    pattern = r'(<p style="margin-bottom: 2rem; max-width: 60ch; color: var\(--muted\);">.*?</p>\s*)(.*?)(\s*</section>)'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        raise ValueError("Could not find positions section pattern in HTML. Has the intro <p> changed?")

    new_content = content[:match.start()] + match.group(1) + cards + "\n      " + match.group(3) + content[match.end():]

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return len(active)


class ManagePositionsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Manage Open Positions")
        self.root.geometry("640x840")
        self.selected_image_path = ""
        self.selected_attachment_path = ""
        self.editing_filename = None

        os.makedirs(POSITIONS_DIR, exist_ok=True)

        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Position List ---
        list_frame = ttk.LabelFrame(main_frame, text="Existing Positions", padding="5")
        list_frame.pack(fill=tk.BOTH, pady=(0, 5))

        list_btn_frame = ttk.Frame(list_frame)
        list_btn_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(list_btn_frame, text="Add New", command=self.add_position).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(list_btn_frame, text="Edit Selected", command=self.edit_position).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(list_btn_frame, text="Delete Selected", command=self.delete_position).pack(side=tk.LEFT)

        self.listbox = tk.Listbox(list_frame, height=6, font=("Consolas", 10))
        self.listbox.pack(fill=tk.BOTH, expand=True)

        # --- Position Details ---
        det_frame = ttk.LabelFrame(main_frame, text="Position Details", padding="10")
        det_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 5))

        ttk.Label(det_frame, text="Title:").grid(row=0, column=0, sticky="w", pady=2)
        self.title_entry = ttk.Entry(det_frame, width=42)
        self.title_entry.grid(row=0, column=1, pady=2, sticky="w")

        ttk.Label(det_frame, text="Status:").grid(row=1, column=0, sticky="w", pady=2)
        self.status_combo = ttk.Combobox(det_frame, values=STATUS_OPTIONS, width=39, state="readonly")
        self.status_combo.grid(row=1, column=1, pady=2, sticky="w")
        self.status_combo.current(0)

        ttk.Label(det_frame, text="Description:").grid(row=2, column=0, sticky="nw", pady=2)
        self.desc_text = tk.Text(det_frame, width=40, height=5)
        self.desc_text.grid(row=2, column=1, pady=2, sticky="w")

        ttk.Label(det_frame, text="Image:").grid(row=3, column=0, sticky="w", pady=2)
        img_frame = ttk.Frame(det_frame)
        img_frame.grid(row=3, column=1, sticky="w", pady=2)
        ttk.Button(img_frame, text="Select Image...", command=self.select_image).pack(side=tk.LEFT)
        self.image_label = ttk.Label(img_frame, text="No image selected", font=("Arial", 8), foreground="gray")
        self.image_label.pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(det_frame, text="Attachment:").grid(row=4, column=0, sticky="w", pady=2)
        att_frame = ttk.Frame(det_frame)
        att_frame.grid(row=4, column=1, sticky="w", pady=2)
        ttk.Button(att_frame, text="Select File...", command=self.select_attachment).pack(side=tk.LEFT)
        self.attachment_label = ttk.Label(att_frame, text="No file selected", font=("Arial", 8), foreground="gray")
        self.attachment_label.pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(det_frame, text="Public:").grid(row=5, column=0, sticky="w", pady=2)
        self.public_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(det_frame, text="Show on website", variable=self.public_var).grid(row=5, column=1, sticky="w", pady=2)

        ttk.Label(det_frame, text="Day limit:").grid(row=6, column=0, sticky="w", pady=2)
        lim_frame = ttk.Frame(det_frame)
        lim_frame.grid(row=6, column=1, sticky="w", pady=2)
        self.limit_spin = ttk.Spinbox(lim_frame, from_=0, to=9999, width=8)
        self.limit_spin.set(90)
        self.limit_spin.pack(side=tk.LEFT)
        ttk.Label(lim_frame, text="days (0 = no limit)").pack(side=tk.LEFT, padx=(5, 0))

        btn_frame = ttk.Frame(det_frame)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=(10, 0))
        self.save_btn = ttk.Button(btn_frame, text="Save Position", command=self.save_position)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear Form", command=self.clear_form).pack(side=tk.LEFT, padx=5)

        # --- Generate ---
        gen_frame = ttk.LabelFrame(main_frame, text="Generate Webpage", padding="5")
        gen_frame.pack(fill=tk.X, pady=(5, 0))

        self.gen_status = ttk.Label(gen_frame, text="", font=("Arial", 9))
        self.gen_status.pack(anchor="w", pady=(0, 5))

        ttk.Button(gen_frame, text="Generate positions.html", command=self.generate_page).pack()

        self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        self.positions = list_positions()
        for f, d in self.positions:
            title = d.get("title", "[error]")
            status = d.get("status", "")
            active = is_active(d)
            padded_status = status[:22].ljust(22)
            display = f"  {padded_status}  {title}"
            self.listbox.insert(tk.END, display)

    def add_position(self):
        self.editing_filename = None
        self.clear_form()
        self.title_entry.focus()

    def edit_position(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a position to edit.")
            return
        idx = sel[0]
        filename, data = self.positions[idx]
        self.editing_filename = filename
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, data.get("title", ""))
        status = data.get("status", "")
        if status in STATUS_OPTIONS:
            self.status_combo.set(status)
        else:
            self.status_combo.current(0)
        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert("1.0", data.get("description", ""))
        self.public_var.set(data.get("public", True))
        self.limit_spin.set(data.get("day_limit", 90))
        img = data.get("image", "")
        if img:
            abs_img = os.path.join(BASE_DIR, img)
            if os.path.exists(abs_img):
                self.selected_image_path = abs_img
                self.image_label.config(text=os.path.basename(img))
            else:
                self.selected_image_path = ""
                self.image_label.config(text="Image file missing")
        else:
            self.selected_image_path = ""
            self.image_label.config(text="No image selected")

        att = data.get("attachment", "")
        if att:
            abs_att = os.path.join(BASE_DIR, att)
            if os.path.exists(abs_att):
                self.selected_attachment_path = abs_att
                self.attachment_label.config(text=os.path.basename(att))
            else:
                self.selected_attachment_path = ""
                self.attachment_label.config(text="Attachment file missing")
        else:
            self.selected_attachment_path = ""
            self.attachment_label.config(text="No file selected")

    def delete_position(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a position to delete.")
            return
        idx = sel[0]
        filename, data = self.positions[idx]
        title = data.get("title", filename)
        if not messagebox.askyesno("Confirm Delete", f"Delete position \"{title}\"?"):
            return
        try:
            delete_position_file(filename)
            self.refresh_list()
            self.clear_form()
            messagebox.showinfo("Deleted", f"\"{title}\" deleted.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")

    def select_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=(("Image files", "*.jpg *.jpeg *.png *.gif *.webp"), ("All files", "*.*"))
        )
        if file_path:
            self.selected_image_path = file_path
            self.image_label.config(text=os.path.basename(file_path))

    def select_attachment(self):
        file_path = filedialog.askopenfilename(
            title="Select Attachment",
            filetypes=(("Documents", "*.pdf *.doc *.docx"), ("All files", "*.*"))
        )
        if file_path:
            self.selected_attachment_path = file_path
            self.attachment_label.config(text=os.path.basename(file_path))

    def save_position(self):
        title = self.title_entry.get().strip()
        status = self.status_combo.get().strip()
        description = self.desc_text.get("1.0", tk.END).strip()

        if not title:
            messagebox.showwarning("Validation", "Title is required.")
            return
        if not status:
            messagebox.showwarning("Validation", "Status is required.")
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
        if self.selected_image_path and self.image_label.cget("text") != "Image file missing":
            abs_selected = os.path.abspath(self.selected_image_path)
            ext = os.path.splitext(self.selected_image_path)[1].lower()
            new_img_name = slugify(title) + ext
            dest_path = os.path.join(POSITIONS_DIR, new_img_name)
            if abs_selected != os.path.abspath(dest_path):
                try:
                    shutil.copy(self.selected_image_path, dest_path)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to copy image: {e}")
                    return
            image_web_path = f"assets/positions/{new_img_name}"

        attachment_web_path = old_attachment if old_attachment else ""
        if self.selected_attachment_path and self.attachment_label.cget("text") != "Attachment file missing":
            abs_selected = os.path.abspath(self.selected_attachment_path)
            ext = os.path.splitext(self.selected_attachment_path)[1].lower()
            new_att_name = slugify(title) + ext
            dest_path = os.path.join(POSITIONS_DIR, new_att_name)
            if abs_selected != os.path.abspath(dest_path):
                try:
                    shutil.copy(self.selected_attachment_path, dest_path)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to copy attachment: {e}")
                    return
            attachment_web_path = f"assets/positions/{new_att_name}"

        data = {
            "title": title,
            "status": status,
            "description": description,
            "image": image_web_path,
            "attachment": attachment_web_path,
            "public": self.public_var.get(),
            "day_limit": int(self.limit_spin.get()),
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
            messagebox.showinfo("Saved", f"\"{title}\" saved.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def clear_form(self):
        self.title_entry.delete(0, tk.END)
        self.status_combo.current(0)
        self.desc_text.delete("1.0", tk.END)
        self.selected_image_path = ""
        self.image_label.config(text="No image selected")
        self.selected_attachment_path = ""
        self.attachment_label.config(text="No file selected")
        self.public_var.set(True)
        self.limit_spin.set(90)
        self.editing_filename = None

    def generate_page(self):
        try:
            count = regenerate_html(HTML_FILE, POSITIONS_DIR)
            git_msg = ""
            try:
                subprocess.run(
                    ["git", "add", HTML_FILE, POSITIONS_DIR],
                    check=True, cwd=BASE_DIR, capture_output=True, text=True
                )
                subprocess.run(
                    ["git", "commit", "-m", f"Update open positions page ({count} active)"],
                    check=True, cwd=BASE_DIR, capture_output=True, text=True
                )
                git_msg = " (committed to Git)"
            except Exception as e:
                git_msg = f" (Git: {e})"

            self.gen_status.config(text=f"OK — {count} active position(s){git_msg}", foreground="green")
            messagebox.showinfo("Success", f"Generated positions.html with {count} active position(s).{git_msg}")
        except Exception as e:
            self.gen_status.config(text=f"Error: {e}", foreground="red")
            messagebox.showerror("Error", f"Failed to generate page: {e}")


if __name__ == "__main__":
    if not os.path.exists(HTML_FILE):
        print(f"Error: {HTML_FILE} not found.")
    else:
        root = tk.Tk()
        app = ManagePositionsGUI(root)
        root.mainloop()
