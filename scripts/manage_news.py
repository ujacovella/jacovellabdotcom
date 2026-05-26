import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil
import os
import re
import json
import subprocess
from datetime import datetime

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
    # Remove associated image
    base = os.path.splitext(path)[0]
    for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
        associated = base + ext
        if os.path.exists(associated):
            os.remove(associated)
    # Remove associated image file
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
    # Sort by date descending, then by filename
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


class ManageNewsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Manage News")
        self.root.geometry("640x780")
        self.selected_image_path = ""
        self.editing_filename = None

        os.makedirs(NEWS_DIR, exist_ok=True)

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

        # --- News List ---
        list_frame = ttk.LabelFrame(main_frame, text="Existing News Items", padding="5")
        list_frame.pack(fill=tk.BOTH, pady=(0, 5))

        list_btn_frame = ttk.Frame(list_frame)
        list_btn_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(list_btn_frame, text="Add New", command=self.add_news).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(list_btn_frame, text="Edit Selected", command=self.edit_news).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(list_btn_frame, text="Delete Selected", command=self.delete_news).pack(side=tk.LEFT)

        self.listbox = tk.Listbox(list_frame, height=6, font=("Consolas", 10))
        self.listbox.pack(fill=tk.BOTH, expand=True)

        # --- News Details ---
        det_frame = ttk.LabelFrame(main_frame, text="News Details", padding="10")
        det_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 5))

        ttk.Label(det_frame, text="Title: *").grid(row=0, column=0, sticky="w", pady=2)
        self.title_entry = ttk.Entry(det_frame, width=50)
        self.title_entry.grid(row=0, column=1, pady=2, sticky="w")

        ttk.Label(det_frame, text="Date: *").grid(row=1, column=0, sticky="w", pady=2)
        date_frame = ttk.Frame(det_frame)
        date_frame.grid(row=1, column=1, sticky="w", pady=2)
        self.year_spin = ttk.Spinbox(date_frame, from_=2020, to=2100, width=6)
        self.year_spin.set(str(datetime.now().year))
        self.year_spin.pack(side=tk.LEFT)
        ttk.Label(date_frame, text="-").pack(side=tk.LEFT, padx=2)
        self.month_spin = ttk.Spinbox(date_frame, from_=1, to=12, width=4, format="%02.0f")
        self.month_spin.set(f"{datetime.now().month:02d}")
        self.month_spin.pack(side=tk.LEFT)
        ttk.Label(date_frame, text="-").pack(side=tk.LEFT, padx=2)
        self.day_spin = ttk.Spinbox(date_frame, from_=1, to=31, width=4, format="%02.0f")
        self.day_spin.set(f"{datetime.now().day:02d}")
        self.day_spin.pack(side=tk.LEFT)
        ttk.Label(date_frame, text="  (YYYY-MM-DD)").pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(det_frame, text="Excerpt:").grid(row=2, column=0, sticky="nw", pady=2)
        self.excerpt_text = tk.Text(det_frame, width=50, height=6)
        self.excerpt_text.grid(row=2, column=1, pady=2, sticky="w")

        ttk.Label(det_frame, text="Image:").grid(row=3, column=0, sticky="w", pady=2)
        img_frame = ttk.Frame(det_frame)
        img_frame.grid(row=3, column=1, sticky="w", pady=2)
        ttk.Button(img_frame, text="Select Image...", command=self.select_image).pack(side=tk.LEFT)
        self.image_label = ttk.Label(img_frame, text="No image selected", font=("Arial", 8), foreground="gray")
        self.image_label.pack(side=tk.LEFT, padx=(5, 0))

        btn_frame = ttk.Frame(det_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        self.save_btn = ttk.Button(btn_frame, text="Save News", command=self.save_news)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear Form", command=self.clear_form).pack(side=tk.LEFT, padx=5)

        # --- Generate ---
        gen_frame = ttk.LabelFrame(main_frame, text="Generate Webpage", padding="5")
        gen_frame.pack(fill=tk.X, pady=(5, 0))

        self.gen_status = ttk.Label(gen_frame, text="", font=("Arial", 9))
        self.gen_status.pack(anchor="w", pady=(0, 5))

        ttk.Button(gen_frame, text="Generate news.html", command=self.generate_page).pack()

        self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        self.news_items = list_news()
        for f, d in self.news_items:
            title = d.get("title", "[error]")
            date_str = d.get("date", "")
            display = format_display_date(date_str)
            padded_date = (display[:18].ljust(18))
            self.listbox.insert(tk.END, f"  {padded_date}  {title}")

    def add_news(self):
        self.editing_filename = None
        self.clear_form()
        self.title_entry.focus()

    def edit_news(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a news item to edit.")
            return
        idx = sel[0]
        filename, data = self.news_items[idx]
        self.editing_filename = filename
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, data.get("title", ""))
        date_str = data.get("date", "")
        parts = date_str.split("-")
        if len(parts) == 3:
            self.year_spin.set(parts[0])
            self.month_spin.set(parts[1])
            self.day_spin.set(parts[2])
        elif len(parts) == 2:
            self.year_spin.set(parts[0])
            self.month_spin.set(parts[1])
            self.day_spin.set("01")
        self.excerpt_text.delete("1.0", tk.END)
        self.excerpt_text.insert("1.0", data.get("excerpt", ""))

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

    def delete_news(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a news item to delete.")
            return
        idx = sel[0]
        filename, data = self.news_items[idx]
        title = data.get("title", filename)
        if not messagebox.askyesno("Confirm Delete", f"Delete news item \"{title}\"?"):
            return
        try:
            delete_news_file(filename)
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

    def save_news(self):
        title = self.title_entry.get().strip()
        year = self.year_spin.get().strip()
        month = self.month_spin.get().strip()
        day = self.day_spin.get().strip()
        excerpt = self.excerpt_text.get("1.0", tk.END).strip()

        if not title:
            messagebox.showwarning("Validation", "Title is required.")
            return
        try:
            y = int(year)
            m = int(month)
            d = int(day)
            if not (1 <= m <= 12 and 1 <= d <= 31):
                raise ValueError
        except ValueError:
            messagebox.showwarning("Validation", "Invalid date. Use YYYY-MM-DD.")
            return

        date_str = f"{y:04d}-{m:02d}-{d:02d}"

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
        if self.selected_image_path and self.image_label.cget("text") != "Image file missing":
            abs_selected = os.path.abspath(self.selected_image_path)
            ext = os.path.splitext(self.selected_image_path)[1].lower()
            new_img_name = slugify(title) + ext
            dest_path = os.path.join(NEWS_DIR, new_img_name)
            if abs_selected != os.path.abspath(dest_path):
                try:
                    shutil.copy(self.selected_image_path, dest_path)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to copy image: {e}")
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
            messagebox.showinfo("Saved", f"\"{title}\" saved.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def clear_form(self):
        self.title_entry.delete(0, tk.END)
        self.year_spin.set(str(datetime.now().year))
        self.month_spin.set(f"{datetime.now().month:02d}")
        self.day_spin.set(f"{datetime.now().day:02d}")
        self.excerpt_text.delete("1.0", tk.END)
        self.selected_image_path = ""
        self.image_label.config(text="No image selected")
        self.editing_filename = None

    def generate_page(self):
        try:
            count = regenerate_html()
            git_msg = ""
            try:
                subprocess.run(
                    ["git", "add", HTML_FILE, NEWS_DIR],
                    check=True, cwd=BASE_DIR, capture_output=True, text=True
                )
                subprocess.run(
                    ["git", "commit", "-m", f"Update news page ({count} items)"],
                    check=True, cwd=BASE_DIR, capture_output=True, text=True
                )
                git_msg = " (committed to Git)"
            except Exception as e:
                git_msg = f" (Git: {e})"

            self.gen_status.config(text=f"OK \u2014 {count} news item(s){git_msg}", foreground="green")
            messagebox.showinfo("Success", f"Generated news.html with {count} item(s).{git_msg}")
        except Exception as e:
            self.gen_status.config(text=f"Error: {e}", foreground="red")
            messagebox.showerror("Error", f"Failed to generate page: {e}")


if __name__ == "__main__":
    if not os.path.exists(HTML_FILE):
        print(f"Error: {HTML_FILE} not found.")
    else:
        root = tk.Tk()
        app = ManageNewsGUI(root)
        root.mainloop()
