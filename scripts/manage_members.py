import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil
import os
import re
import json
import subprocess

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
    if given: initials += given[0].upper()
    if middle: initials += middle[0].upper()
    if last: initials += last[0].upper()
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

    # --- Update group.html ---
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

    # --- Update theses.html ---
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


class ManageMembersGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Manage Group Members")
        self.root.geometry("640x840")
        self.selected_photo_path = ""
        self.editing_filename = None

        os.makedirs(MEMBERS_DIR, exist_ok=True)
        os.makedirs(PHOTOS_DIR, exist_ok=True)

        # --- Scrollable wrapper ---
        outer = ttk.Frame(root)
        outer.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(outer, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollable_frame = ttk.Frame(self.canvas, padding="10")
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        def _on_canvas_configure(e):
            self.canvas.itemconfig(self.canvas.find_withtag("all")[0], width=e.width)
        self.canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            if event.delta:
                self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        main_frame = self.scrollable_frame

        # --- Member List ---
        list_frame = ttk.LabelFrame(main_frame, text="Existing Members", padding="5")
        list_frame.pack(fill=tk.BOTH, pady=(0, 5))

        list_btn_frame = ttk.Frame(list_frame)
        list_btn_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(list_btn_frame, text="Add New", command=self.add_member).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(list_btn_frame, text="Edit Selected", command=self.edit_member).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(list_btn_frame, text="Delete Selected", command=self.delete_member).pack(side=tk.LEFT)

        self.listbox = tk.Listbox(list_frame, height=6, font=("Consolas", 10))
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)

        # --- Member Details ---
        det_frame = ttk.LabelFrame(main_frame, text="Member Details", padding="10")
        det_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 5))

        # Row 0: Title
        ttk.Label(det_frame, text="Title:").grid(row=0, column=0, sticky="w", pady=2)
        self.title_combo = ttk.Combobox(det_frame, values=["", "Dr.", "Prof.", "Mr.", "Ms."], width=27)
        self.title_combo.current(0)
        self.title_combo.grid(row=0, column=1, pady=2, sticky="w")

        # Row 1: Given Name
        ttk.Label(det_frame, text="Given Name: *").grid(row=1, column=0, sticky="w", pady=2)
        self.given_entry = ttk.Entry(det_frame, width=30)
        self.given_entry.grid(row=1, column=1, pady=2, sticky="w")

        # Row 2: Middle Name
        ttk.Label(det_frame, text="Middle Name:").grid(row=2, column=0, sticky="w", pady=2)
        self.middle_entry = ttk.Entry(det_frame, width=30)
        self.middle_entry.grid(row=2, column=1, pady=2, sticky="w")

        # Row 3: Last Name
        ttk.Label(det_frame, text="Last Name: *").grid(row=3, column=0, sticky="w", pady=2)
        self.last_entry = ttk.Entry(det_frame, width=30)
        self.last_entry.grid(row=3, column=1, pady=2, sticky="w")

        # Row 4: Role
        ttk.Label(det_frame, text="Role: *").grid(row=4, column=0, sticky="w", pady=2)
        self.role_combo = ttk.Combobox(det_frame, values=ROLE_OPTIONS, width=27, state="readonly")
        self.role_combo.current(0)
        self.role_combo.grid(row=4, column=1, pady=2, sticky="w")

        # Row 5: Alumni
        ttk.Label(det_frame, text="Status:").grid(row=5, column=0, sticky="w", pady=2)
        self.alumni_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(det_frame, text="Alumni?", variable=self.alumni_var).grid(row=5, column=1, sticky="w", pady=2)

        ttk.Separator(det_frame, orient='horizontal').grid(row=6, column=0, columnspan=2, sticky="ew", pady=8)

        # Row 7: Email
        ttk.Label(det_frame, text="Email:").grid(row=7, column=0, sticky="w", pady=2)
        self.email_entry = ttk.Entry(det_frame, width=30)
        self.email_entry.grid(row=7, column=1, pady=2, sticky="w")

        # Row 8: Training 1
        ttk.Label(det_frame, text="Training Line 1:").grid(row=8, column=0, sticky="w", pady=2)
        self.master_entry = ttk.Entry(det_frame, width=30)
        self.master_entry.grid(row=8, column=1, pady=2, sticky="w")

        # Row 9: Training 2
        ttk.Label(det_frame, text="Training Line 2:").grid(row=9, column=0, sticky="w", pady=2)
        self.phd_entry = ttk.Entry(det_frame, width=30)
        self.phd_entry.grid(row=9, column=1, pady=2, sticky="w")

        # Row 10: Project
        ttk.Label(det_frame, text="Current Project:").grid(row=10, column=0, sticky="w", pady=2)
        self.project_text = tk.Text(det_frame, width=30, height=3)
        self.project_text.grid(row=10, column=1, pady=2, sticky="w")

        ttk.Separator(det_frame, orient='horizontal').grid(row=11, column=0, columnspan=2, sticky="ew", pady=8)

        # Row 12: Photo
        ttk.Label(det_frame, text="Photo:").grid(row=12, column=0, sticky="w", pady=2)
        photo_frame = ttk.Frame(det_frame)
        photo_frame.grid(row=12, column=1, sticky="w", pady=2)
        ttk.Button(photo_frame, text="Select Photo...", command=self.select_photo).pack(side=tk.LEFT)
        self.photo_label = ttk.Label(photo_frame, text="No photo selected", font=("Arial", 8), foreground="gray")
        self.photo_label.pack(side=tk.LEFT, padx=(5, 0))

        ttk.Separator(det_frame, orient='horizontal').grid(row=13, column=0, columnspan=2, sticky="ew", pady=8)

        # Row 14: Thesis Title
        ttk.Label(det_frame, text="PhD Title:").grid(row=14, column=0, sticky="w", pady=2)
        self.thesis_title_entry = ttk.Entry(det_frame, width=30)
        self.thesis_title_entry.grid(row=14, column=1, pady=2, sticky="w")

        # Row 15: Thesis Link
        ttk.Label(det_frame, text="Thesis Link:").grid(row=15, column=0, sticky="w", pady=2)
        self.thesis_link_entry = ttk.Entry(det_frame, width=30)
        self.thesis_link_entry.grid(row=15, column=1, pady=2, sticky="w")

        # Row 16: PhD Completed
        ttk.Label(det_frame, text="PhD Completed?").grid(row=16, column=0, sticky="w", pady=2)
        self.phd_completed_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(det_frame, text="Yes", variable=self.phd_completed_var).grid(row=16, column=1, sticky="w", pady=2)

        # Buttons
        btn_frame = ttk.Frame(det_frame)
        btn_frame.grid(row=17, column=0, columnspan=2, pady=(10, 0))
        self.save_btn = ttk.Button(btn_frame, text="Save Member", command=self.save_member)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear Form", command=self.clear_form).pack(side=tk.LEFT, padx=5)

        # --- Generate ---
        gen_frame = ttk.LabelFrame(main_frame, text="Generate Webpage", padding="5")
        gen_frame.pack(fill=tk.X, pady=(5, 0))

        self.gen_status = ttk.Label(gen_frame, text="", font=("Arial", 9))
        self.gen_status.pack(anchor="w", pady=(0, 5))

        ttk.Button(gen_frame, text="Generate group.html & theses.html", command=self.generate_page).pack()

        self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        self.members = list_members()
        for f, d in self.members:
            name = format_name(d)
            role = d.get("role", "")
            alumni = " [Alumni]" if d.get("alumni", False) else ""
            padded_role = role[:22].ljust(22)
            display = f"  {padded_role}  {name}{alumni}"
            self.listbox.insert(tk.END, display)

    def on_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        filename, data = self.members[idx]
        self.load_member_to_form(filename, data)

    def load_member_to_form(self, filename, data):
        self.editing_filename = filename
        title = data.get("title", "")
        if title in ["", "Dr.", "Prof.", "Mr.", "Ms."]:
            self.title_combo.set(title)
        else:
            self.title_combo.set("")

        self.given_entry.delete(0, tk.END)
        self.given_entry.insert(0, data.get("given", ""))
        self.middle_entry.delete(0, tk.END)
        self.middle_entry.insert(0, data.get("middle", ""))
        self.last_entry.delete(0, tk.END)
        self.last_entry.insert(0, data.get("last", ""))

        role = data.get("role", "")
        if role in ROLE_OPTIONS:
            self.role_combo.set(role)
        else:
            self.role_combo.current(0)

        self.alumni_var.set(data.get("alumni", False))
        self.email_entry.delete(0, tk.END)
        self.email_entry.insert(0, data.get("email", ""))
        self.master_entry.delete(0, tk.END)
        self.master_entry.insert(0, data.get("master", ""))
        self.phd_entry.delete(0, tk.END)
        self.phd_entry.insert(0, data.get("phd", ""))
        self.project_text.delete("1.0", tk.END)
        self.project_text.insert("1.0", data.get("project", ""))

        photo = data.get("photo", "")
        if photo:
            abs_photo = os.path.join(BASE_DIR, photo)
            if os.path.exists(abs_photo):
                self.selected_photo_path = abs_photo
                self.photo_label.config(text=os.path.basename(photo))
            else:
                self.selected_photo_path = ""
                self.photo_label.config(text="Photo file missing")
        else:
            self.selected_photo_path = ""
            self.photo_label.config(text="No photo selected")

        self.thesis_title_entry.delete(0, tk.END)
        self.thesis_title_entry.insert(0, data.get("thesis_title", ""))
        self.thesis_link_entry.delete(0, tk.END)
        self.thesis_link_entry.insert(0, data.get("thesis_link", ""))
        self.phd_completed_var.set(data.get("phd_completed", False))

    def add_member(self):
        self.editing_filename = None
        self.clear_form()
        self.given_entry.focus()

    def edit_member(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a member to edit.")
            return
        idx = sel[0]
        filename, data = self.members[idx]
        self.load_member_to_form(filename, data)

    def delete_member(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a member to delete.")
            return
        idx = sel[0]
        filename, data = self.members[idx]
        name = format_name(data)
        if not messagebox.askyesno("Confirm Delete", f'Delete member "{name}"?'):
            return
        try:
            delete_member_file(filename)
            self.refresh_list()
            self.clear_form()
            messagebox.showinfo("Deleted", f'"{name}" deleted.')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")

    def select_photo(self):
        file_path = filedialog.askopenfilename(
            title="Select Photo",
            filetypes=(("Image files", "*.jpg *.jpeg *.png *.gif *.webp"), ("All files", "*.*"))
        )
        if file_path:
            self.selected_photo_path = file_path
            self.photo_label.config(text=os.path.basename(file_path))

    def save_member(self):
        title = self.title_combo.get().strip()
        given = self.given_entry.get().strip()
        middle = self.middle_entry.get().strip()
        last = self.last_entry.get().strip()
        role = self.role_combo.get().strip()
        email = self.email_entry.get().strip()
        master = self.master_entry.get().strip()
        phd = self.phd_entry.get().strip()
        project = self.project_text.get("1.0", tk.END).strip()
        thesis_title = self.thesis_title_entry.get().strip()
        thesis_link = self.thesis_link_entry.get().strip()

        if not given or not last or not role:
            messagebox.showwarning("Validation", "Given Name, Last Name, and Role are required.")
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
        if self.selected_photo_path and self.photo_label.cget("text") != "Photo file missing":
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
                    messagebox.showerror("Error", f"Failed to copy photo: {e}")
                    return
            photo_web_path = f"assets/group/{new_photo_name}"

        data = {
            "title": title,
            "given": given,
            "middle": middle,
            "last": last,
            "role": role,
            "alumni": self.alumni_var.get(),
            "email": email,
            "master": master,
            "phd": phd,
            "project": project,
            "photo": photo_web_path,
            "thesis_title": thesis_title,
            "thesis_link": thesis_link,
            "phd_completed": self.phd_completed_var.get(),
        }

        try:
            save_member(filename, data)
            self.editing_filename = filename
            self.refresh_list()
            messagebox.showinfo("Saved", f'"{format_name(data)}" saved.')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def clear_form(self):
        self.title_combo.set("")
        self.given_entry.delete(0, tk.END)
        self.middle_entry.delete(0, tk.END)
        self.last_entry.delete(0, tk.END)
        self.role_combo.current(0)
        self.alumni_var.set(False)
        self.email_entry.delete(0, tk.END)
        self.master_entry.delete(0, tk.END)
        self.phd_entry.delete(0, tk.END)
        self.project_text.delete("1.0", tk.END)
        self.selected_photo_path = ""
        self.photo_label.config(text="No photo selected")
        self.thesis_title_entry.delete(0, tk.END)
        self.thesis_link_entry.delete(0, tk.END)
        self.phd_completed_var.set(False)
        self.editing_filename = None

    def generate_page(self):
        try:
            count = regenerate_html()
            git_msg = ""
            try:
                subprocess.run(
                    ["git", "add", HTML_FILE, THESES_FILE],
                    check=True, cwd=BASE_DIR, capture_output=True, text=True
                )
                subprocess.run(
                    ["git", "commit", "-m", f"Update group members page ({count} members)"],
                    check=True, cwd=BASE_DIR, capture_output=True, text=True
                )
                git_msg = " (committed to Git)"
            except Exception as e:
                git_msg = f" (Git: {e})"

            self.gen_status.config(text=f"OK — {count} member(s){git_msg}", foreground="green")
            messagebox.showinfo("Success", f"Generated group.html and theses.html with {count} member(s).{git_msg}")
        except Exception as e:
            self.gen_status.config(text=f"Error: {e}", foreground="red")
            messagebox.showerror("Error", f"Failed to generate page: {e}")


if __name__ == "__main__":
    if not os.path.exists(HTML_FILE):
        print(f"Error: {HTML_FILE} not found.")
    else:
        root = tk.Tk()
        app = ManageMembersGUI(root)
        root.mainloop()
