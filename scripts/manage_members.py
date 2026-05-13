import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil
import os
import re
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_FILE = os.path.join(BASE_DIR, "group.html")
THESES_FILE = os.path.join(BASE_DIR, "theses.html")
ASSETS_DIR = os.path.join(BASE_DIR, "assets", "group")

def get_initials(given, middle, last):
    initials = ""
    if given: initials += given[0].upper()
    if middle: initials += middle[0].upper()
    if last: initials += last[0].upper()
    return initials

def format_name(given, middle, last):
    parts = []
    if given: parts.append(given)
    if middle: parts.append(middle)
    if last: parts.append(last)
    return " ".join(parts)

def insert_member_into_html(html_content, member_html):
    section_id = "members"
    pattern = rf'(<section id="{section_id}"[^>]*>.*?<div class="group-grid">)(.*?)(      </div>\s*</section>)'
    match = re.search(pattern, html_content, re.DOTALL)
    
    if match:
        before = match.group(1)
        content = match.group(2)
        after = match.group(3)
        
        new_content = content.rstrip() + "\n" + member_html + "\n"
        
        return html_content[:match.start()] + before + new_content + after + html_content[match.end():]
    else:
        raise ValueError("Could not find <section id='members'> with <div class='group-grid'> inside.")

def insert_thesis_into_html(theses_file, name, thesis_title, thesis_link, is_phd_completed):
    with open(theses_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Decide which section: Ongoing or Completed
    if is_phd_completed:
        heading = "Completed Theses"
    else:
        heading = "Ongoing PhD Theses"

    pattern = rf'(<h3[^>]*>\s*{heading}\s*</h3>)(.*?)(</div>)'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find section for '{heading}' in theses.html")

    before = content[:match.start()]
    h3 = match.group(1)
    inner_content = match.group(2)
    after = match.group(3) + content[match.end():]

    href_attr = f' href="{thesis_link}" target="_blank" rel="noopener noreferrer"' if thesis_link else ""
    tag = "a" if thesis_link else "span"
    link_style = "text-decoration: none; color: var(--accent);" if thesis_link else "color: var(--text);"
    
    new_li = f'''          <li style="padding: 1rem; border: 1px solid var(--border); border-radius: var(--radius); margin-bottom: 1rem;">
            <strong>{name}</strong><br>
            <{tag}{href_attr} style="{link_style} font-size: 14px;">"{thesis_title}"</{tag}>
          </li>\n'''

    if "<p" in inner_content and "List of completed" in inner_content:
        inner_content = '\n        <ul style="list-style: none; padding-left: 0;">\n' + new_li + '        </ul>\n      '
    else:
        ul_match = re.search(r'(<ul[^>]*>)(.*?)(</ul>)', inner_content, re.DOTALL)
        if ul_match:
            ul_before = inner_content[:ul_match.start()]
            ul_start = ul_match.group(1)
            ul_inner = ul_match.group(2)
            ul_end = ul_match.group(3)
            ul_after = inner_content[ul_match.end():]
            inner_content = ul_before + ul_start + ul_inner.rstrip() + "\n" + new_li + "        " + ul_end + ul_after
        else:
            inner_content += '\n        <ul style="list-style: none; padding-left: 0;">\n' + new_li + '        </ul>\n      '

    new_content = before + h3 + inner_content + after
    with open(theses_file, "w", encoding="utf-8") as f:
        f.write(new_content)

def generate_html(title, given, middle, last, role, is_alumni, photo_path, thesis_title, thesis_link, email, master, phd, project):
    name = format_name(given, middle, last)
    display_name = f"{title} {name}".strip() if title else name
    initials = get_initials(given, middle, last)
    
    if is_alumni:
        bg_color = "#f5f5f7"
        text_color = "#86868b"
        opacity_style = ' style="opacity: 0.7;"'
    else:
        colors = [
            ("#dce8f8", "#1a4080"), # blue
            ("#d8f0e4", "#1a5c38"), # green
            ("#fef0d4", "#7a4a0a"), # orange
            ("#f3e5f5", "#4a148c"), # purple
            ("#ffebee", "#b71c1c")  # red
        ]
        c_idx = len(name) % len(colors)
        bg_color, text_color = colors[c_idx]
        opacity_style = ''

    html_lines = []
    html_lines.append(f'        <!-- MEMBER START: {name} -->')
    html_lines.append(f'        <div class="member-card" data-pi="false" data-alumni="{str(is_alumni).lower()}"{opacity_style}>')
    
    if photo_path:
        web_path = photo_path.replace("\\", "/")
        html_lines.append(f'          <img src="{web_path}" alt="{name}" class="member-avatar" style="object-fit: cover;">')
    else:
        html_lines.append(f'          <div class="member-avatar" style="background:{bg_color};color:{text_color}">{initials}</div>')
    
    html_lines.append(f'          <div class="member-name">{display_name}</div>')
    html_lines.append(f'          <div class="member-role">{role}</div>')
    
    if thesis_title:
        html_lines.append(f'          <a href="theses.html" class="member-thesis" style="display: block; font-size: 13px; margin-top: 0.5rem; text-decoration: none; color: var(--accent);">{thesis_title}</a>')
        
    html_lines.append(f'          <div class="member-details">')
    html_lines.append(f'            <p class="detail-email">{email}</p>')
    html_lines.append(f'            <p class="detail-master">{master}</p>')
    html_lines.append(f'            <p class="detail-phd">{phd}</p>')
    html_lines.append(f'            <p class="detail-project">{project}</p>')
    html_lines.append(f'          </div>')
    html_lines.append(f'        </div>')
    html_lines.append(f'        <!-- MEMBER END: {name} -->')
    
    return "\n".join(html_lines)


class AddMemberGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Add Group Member")
        self.root.geometry("500x780")
        
        os.makedirs(ASSETS_DIR, exist_ok=True)
        self.selected_photo_path = ""

        frame = ttk.Frame(root, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        # Name / Title
        ttk.Label(frame, text="Title:").grid(row=0, column=0, sticky="w", pady=2)
        self.title_combo = ttk.Combobox(frame, values=["", "Dr.", "Prof.", "Mr.", "Ms."], width=27)
        self.title_combo.current(0)
        self.title_combo.grid(row=0, column=1, pady=2, sticky="w")

        ttk.Label(frame, text="Given Name: *").grid(row=1, column=0, sticky="w", pady=2)
        self.given_entry = ttk.Entry(frame, width=30)
        self.given_entry.grid(row=1, column=1, pady=2, sticky="w")

        ttk.Label(frame, text="Middle Name:").grid(row=2, column=0, sticky="w", pady=2)
        self.middle_entry = ttk.Entry(frame, width=30)
        self.middle_entry.grid(row=2, column=1, pady=2, sticky="w")

        ttk.Label(frame, text="Last Name: *").grid(row=3, column=0, sticky="w", pady=2)
        self.last_entry = ttk.Entry(frame, width=30)
        self.last_entry.grid(row=3, column=1, pady=2, sticky="w")

        # Role / Status
        ttk.Label(frame, text="Role: *").grid(row=4, column=0, sticky="w", pady=2)
        self.role_combo = ttk.Combobox(frame, values=["PhD Student", "Postdoctoral Fellow", "Master Student", "Bachelor Student", "Other"], width=27)
        self.role_combo.current(0)
        self.role_combo.grid(row=4, column=1, pady=2, sticky="w")

        ttk.Label(frame, text="Status:").grid(row=5, column=0, sticky="w", pady=2)
        self.alumni_var = tk.BooleanVar(self.root)
        self.alumni_var.set(False)
        ttk.Checkbutton(frame, text="Alumni?", variable=self.alumni_var, onvalue=True, offvalue=False).grid(row=5, column=1, sticky="w", pady=2)

        # Contact / Training / Info
        ttk.Separator(frame, orient='horizontal').grid(row=6, column=0, columnspan=2, sticky="ew", pady=10)
        
        ttk.Label(frame, text="Email:").grid(row=7, column=0, sticky="w", pady=2)
        self.email_entry = ttk.Entry(frame, width=30)
        self.email_entry.grid(row=7, column=1, pady=2, sticky="w")

        ttk.Label(frame, text="Training Line 1:").grid(row=8, column=0, sticky="w", pady=2)
        self.master_entry = ttk.Entry(frame, width=30)
        self.master_entry.grid(row=8, column=1, pady=2, sticky="w")

        ttk.Label(frame, text="Training Line 2:").grid(row=9, column=0, sticky="w", pady=2)
        self.phd_entry = ttk.Entry(frame, width=30)
        self.phd_entry.grid(row=9, column=1, pady=2, sticky="w")

        ttk.Label(frame, text="Current Project:").grid(row=10, column=0, sticky="w", pady=2)
        self.project_text = tk.Text(frame, width=30, height=3)
        self.project_text.grid(row=10, column=1, pady=2, sticky="w")

        # Photo
        ttk.Separator(frame, orient='horizontal').grid(row=11, column=0, columnspan=2, sticky="ew", pady=10)
        
        ttk.Label(frame, text="Photo:").grid(row=12, column=0, sticky="w", pady=2)
        self.photo_btn = ttk.Button(frame, text="Select Photo...", command=self.select_photo)
        self.photo_btn.grid(row=12, column=1, sticky="w", pady=2)
        self.photo_label = ttk.Label(frame, text="No photo selected", font=("Arial", 8), foreground="gray")
        self.photo_label.grid(row=13, column=1, sticky="w")

        # Thesis
        ttk.Separator(frame, orient='horizontal').grid(row=14, column=0, columnspan=2, sticky="ew", pady=10)
        
        ttk.Label(frame, text="PhD Title:").grid(row=15, column=0, sticky="w", pady=2)
        self.thesis_title_entry = ttk.Entry(frame, width=30)
        self.thesis_title_entry.grid(row=15, column=1, pady=2, sticky="w")

        ttk.Label(frame, text="Thesis Link:").grid(row=16, column=0, sticky="w", pady=2)
        self.thesis_link_entry = ttk.Entry(frame, width=30)
        self.thesis_link_entry.grid(row=16, column=1, pady=2, sticky="w")

        ttk.Label(frame, text="PhD Completed?").grid(row=17, column=0, sticky="w", pady=2)
        self.phd_completed_var = tk.BooleanVar(self.root)
        self.phd_completed_var.set(False)
        ttk.Checkbutton(frame, text="Yes", variable=self.phd_completed_var, onvalue=True, offvalue=False).grid(row=17, column=1, sticky="w", pady=2)

        ttk.Button(frame, text="Add Member", command=self.add_member).grid(row=18, column=0, columnspan=2, pady=20)

    def select_photo(self):
        file_path = filedialog.askopenfilename(
            title="Select Photo",
            filetypes=(("Image files", "*.jpg *.jpeg *.png"), ("All files", "*.*"))
        )
        if file_path:
            self.selected_photo_path = file_path
            self.photo_label.config(text=os.path.basename(file_path))

    def add_member(self):
        title = self.title_combo.get().strip()
        given = self.given_entry.get().strip()
        middle = self.middle_entry.get().strip()
        last = self.last_entry.get().strip()
        role = self.role_combo.get().strip()
        is_alumni = self.alumni_var.get()
        thesis_title = self.thesis_title_entry.get().strip()
        thesis_link = self.thesis_link_entry.get().strip()
        is_phd_completed = self.phd_completed_var.get()
        
        email = self.email_entry.get().strip()
        master = self.master_entry.get().strip()
        phd = self.phd_entry.get().strip()
        project = self.project_text.get("1.0", tk.END).strip()

        if not given or not last or not role:
            messagebox.showwarning("Validation Error", "Given Name, Last Name, and Role are required.")
            return

        photo_dest_web_path = ""
        if self.selected_photo_path:
            ext = os.path.splitext(self.selected_photo_path)[1].lower()
            name_parts = []
            if given: name_parts.append(given)
            if middle: name_parts.append(middle)
            if last: name_parts.append(last)
            safe_name = "_".join(name_parts).lower()
            safe_name = re.sub(r'[^a-z0-9_]', '', safe_name.replace(" ", "_"))
            new_filename = safe_name + ext
            dest_path = os.path.join(ASSETS_DIR, new_filename)
            if os.path.abspath(self.selected_photo_path) != os.path.abspath(dest_path):
                try:
                    shutil.copy(self.selected_photo_path, dest_path)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to copy photo: {e}")
                    return
            photo_dest_web_path = f"assets/group/{new_filename}"

        try:
            with open(HTML_FILE, "r", encoding="utf-8") as f:
                html_content = f.read()

            member_html = generate_html(
                title, given, middle, last, role, is_alumni, photo_dest_web_path, 
                thesis_title, thesis_link, email, master, phd, project
            )
            
            new_html_content = insert_member_into_html(html_content, member_html)

            with open(HTML_FILE, "w", encoding="utf-8") as f:
                f.write(new_html_content)

            # --- Git Automation ---
            try:
                name = f"{given} {last}"
                # Stage files
                subprocess.run(["git", "add", HTML_FILE], check=True, cwd=BASE_DIR)
                if thesis_title:
                    subprocess.run(["git", "add", THESES_FILE], check=True, cwd=BASE_DIR)
                if photo_dest_web_path:
                    # Construct absolute path to the photo to stage it
                    full_photo_path = os.path.join(BASE_DIR, photo_dest_web_path)
                    subprocess.run(["git", "add", full_photo_path], check=True, cwd=BASE_DIR)
                
                # Commit
                commit_msg = f"Add group member: {name}"
                subprocess.run(["git", "commit", "-m", commit_msg], check=True, cwd=BASE_DIR)
                git_status = "\n(Changes automatically committed to Git)"
            except Exception as git_err:
                git_status = f"\n(Warning: Failed to commit to Git: {git_err})"

            messagebox.showinfo("Success", f"Member {given} {last} added successfully!{git_status}")
            self.clear_form()

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    def clear_form(self):
        self.title_combo.set("")
        self.given_entry.delete(0, tk.END)
        self.middle_entry.delete(0, tk.END)
        self.last_entry.delete(0, tk.END)
        self.role_combo.set("PhD Student")
        self.alumni_var.set(False)
        self.selected_photo_path = ""
        self.photo_label.config(text="No photo selected")
        self.thesis_title_entry.delete(0, tk.END)
        self.thesis_link_entry.delete(0, tk.END)
        self.phd_completed_var.set(False)
        self.email_entry.delete(0, tk.END)
        self.master_entry.delete(0, tk.END)
        self.phd_entry.delete(0, tk.END)
        self.project_text.delete("1.0", tk.END)


if __name__ == "__main__":
    if not os.path.exists(HTML_FILE):
        print(f"Error: {HTML_FILE} not found.")
    else:
        root = tk.Tk()
        app = AddMemberGUI(root)
        root.mainloop()
