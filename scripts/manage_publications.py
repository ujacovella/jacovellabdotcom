"""
manage_publications.py
GUI tool (default) to browse publications from assets/publications.bib, select which to
highlight on the homepage, and regenerate publications.html.

CLI subcommands are also available for scripting:
  python manage_publications.py list [--selected]
  python manage_publications.py select|deselect|toggle <bib_id|doi>
  python manage_publications.py generate
  python manage_publications.py interactive
  python manage_publications.py gui
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BIB_FILE = REPO_ROOT / 'assets' / 'publications.bib'
HTML_FILE = REPO_ROOT / 'publications.html'
SELECTION_FILE = REPO_ROOT / 'assets' / 'selected_publications.json'

MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}

LATEX_ACCENT_COMMANDS = [
    (r'\{\\v\{([a-zA-Z])\}\}', lambda m: {'s': 'š', 'S': 'Š', 'z': 'ž', 'Z': 'Ž', 'c': 'č', 'C': 'Č', 'r': 'ř', 'R': 'Ř'}.get(m.group(1), m.group(1))),
    (r'\{\\v\s*([a-zA-Z])\}',   lambda m: {'s': 'š', 'S': 'Š', 'z': 'ž', 'Z': 'Ž', 'c': 'č', 'C': 'Č', 'r': 'ř', 'R': 'Ř'}.get(m.group(1), m.group(1))),
    (r'\{\\H\{([a-zA-Z])\}\}', lambda m: {'o': 'ő', 'O': 'Ő', 'u': 'ű', 'U': 'Ű'}.get(m.group(1), m.group(1))),
    (r'\{\\H\s*([a-zA-Z])\}',   lambda m: {'o': 'ő', 'O': 'Ő', 'u': 'ű', 'U': 'Ű'}.get(m.group(1), m.group(1))),
    (r'\{\\c\{([a-zA-Z])\}\}', lambda m: {'c': 'ç', 'C': 'Ç'}.get(m.group(1), m.group(1))),
    (r'\{\\c\s*([a-zA-Z])\}',   lambda m: {'c': 'ç', 'C': 'Ç'}.get(m.group(1), m.group(1))),
    (r"\{\\'\{([a-zA-Z])\}\}", lambda m: {'a': 'á', 'e': 'é', 'i': 'í', 'o': 'ó', 'u': 'ú', 'y': 'ý', 'c': 'ć', 'n': 'ń', 'A': 'Á', 'E': 'É', 'I': 'Í', 'O': 'Ó', 'U': 'Ú', 'Y': 'Ý', 'C': 'Ć', 'N': 'Ń'}.get(m.group(1), m.group(1))),
    (r"\{\\'\s*([a-zA-Z])\}",   lambda m: {'a': 'á', 'e': 'é', 'i': 'í', 'o': 'ó', 'u': 'ú', 'y': 'ý', 'c': 'ć', 'n': 'ń', 'A': 'Á', 'E': 'É', 'I': 'Í', 'O': 'Ó', 'U': 'Ú', 'Y': 'Ý', 'C': 'Ć', 'N': 'Ń'}.get(m.group(1), m.group(1))),
    (r'\{\\`\{([a-zA-Z])\}\}', lambda m: {'a': 'à', 'e': 'è', 'i': 'ì', 'o': 'ò', 'u': 'ù', 'A': 'À', 'E': 'È', 'I': 'Ì', 'O': 'Ò', 'U': 'Ù'}.get(m.group(1), m.group(1))),
    (r'\{\\`\s*([a-zA-Z])\}',   lambda m: {'a': 'à', 'e': 'è', 'i': 'ì', 'o': 'ò', 'u': 'ù', 'A': 'À', 'E': 'È', 'I': 'Ì', 'O': 'Ò', 'U': 'Ù'}.get(m.group(1), m.group(1))),
    (r'\{\\\^\{([a-zA-Z])\}\}', lambda m: {'a': 'â', 'e': 'ê', 'i': 'î', 'o': 'ô', 'u': 'û', 'A': 'Â', 'E': 'Ê', 'I': 'Î', 'O': 'Ô', 'U': 'Û'}.get(m.group(1), m.group(1))),
    (r'\{\\\^\s*([a-zA-Z])\}',   lambda m: {'a': 'â', 'e': 'ê', 'i': 'î', 'o': 'ô', 'u': 'û', 'A': 'Â', 'E': 'Ê', 'I': 'Î', 'O': 'Ô', 'U': 'Û'}.get(m.group(1), m.group(1))),
    (r'\{\\"\{([a-zA-Z])\}\}', lambda m: {'a': 'ä', 'e': 'ë', 'i': 'ï', 'o': 'ö', 'u': 'ü', 'A': 'Ä', 'E': 'Ë', 'I': 'Ï', 'O': 'Ö', 'U': 'Ü'}.get(m.group(1), m.group(1))),
    (r'\{\\"\s*([a-zA-Z])\}',   lambda m: {'a': 'ä', 'e': 'ë', 'i': 'ï', 'o': 'ö', 'u': 'ü', 'A': 'Ä', 'E': 'Ë', 'I': 'Ï', 'O': 'Ö', 'U': 'Ü'}.get(m.group(1), m.group(1))),
    (r'\{\\\~\{([a-zA-Z])\}\}', lambda m: {'a': 'ã', 'n': 'ñ', 'o': 'õ', 'A': 'Ã', 'N': 'Ñ', 'O': 'Õ'}.get(m.group(1), m.group(1))),
    (r'\{\\\~\s*([a-zA-Z])\}',   lambda m: {'a': 'ã', 'n': 'ñ', 'o': 'õ', 'A': 'Ã', 'N': 'Ñ', 'O': 'Õ'}.get(m.group(1), m.group(1))),
]


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ── BibTeX parser ────────────────────────────────────────────────────────────

def parse_bib(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    entries = []
    entry_re = re.compile(r'@(\w+)\{')

    for m in entry_re.finditer(text):
        entry_type = m.group(1).lower()
        body_start = m.end()

        depth = 1
        i = body_start
        while i < len(text) and depth > 0:
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
            i += 1
        body = text[body_start:i - 1]

        key_match = re.match(r'\s*([^,]+)', body)
        key = key_match.group(1).strip() if key_match else ''

        entry = {'ID': key, 'ENTRYTYPE': entry_type}

        field_re = re.compile(r'(\w+)\s*=\s*')
        pos = key_match.end() if key_match else 0

        while pos < len(body):
            fm = field_re.search(body, pos)
            if not fm:
                break
            name = fm.group(1).lower()
            val_start = fm.end()
            if val_start >= len(body):
                break

            if body[val_start] == '{':
                depth = 1
                j = val_start + 1
                while j < len(body) and depth > 0:
                    if body[j] == '{':
                        depth += 1
                    elif body[j] == '}':
                        depth -= 1
                    j += 1
                value = body[val_start + 1:j - 1]
                pos = j
            elif body[val_start] == '"':
                j = body.find('"', val_start + 1)
                value = body[val_start + 1:j] if j != -1 else body[val_start + 1:]
                pos = j + 1 if j != -1 else len(body)
            else:
                j = val_start
                while j < len(body) and body[j] not in ',\n\r}':
                    j += 1
                value = body[val_start:j].strip()
                pos = j

            entry[name] = value

        if entry_type in ('article', 'inproceedings', 'proceedings', 'incollection',
                          'book', 'inbook', 'phdthesis', 'mastersthesis', 'techreport',
                          'unpublished', 'misc'):
            entries.append(entry)

    return entries


# ── LaTeX cleaning ───────────────────────────────────────────────────────────

def clean_latex(text):
    if not text:
        return ''
    text = re.sub(r'\{\{(.+?)\}\}', r'\1', text)
    for pattern, repl in LATEX_ACCENT_COMMANDS:
        text = re.sub(pattern, repl, text)
    # Convert sub/superscripts to HTML *before* stripping generic braces, so
    # chemical formulas (e.g. C{\textsubscript{6}}H{\textsubscript{4}}) keep
    # their markup. Tolerates the optional wrapping braces Zotero emits.
    text = re.sub(r'\{?\\textsubscript\s*\{([^{}]*)\}\}?', r'<sub>\1</sub>', text)
    text = re.sub(r'\{?\\textsuperscript\s*\{([^{}]*)\}\}?', r'<sup>\1</sup>', text)
    # Unwrap emphasis (and the braces Zotero wraps it in) before the generic
    # brace strip, otherwise "{\emph{n}}" collapses to "\emphn" and is dropped.
    text = re.sub(r'\{?\\(?:emph|textit)\s*\{([^{}]*)\}\}?', r'\1', text)
    text = re.sub(r'\\textleftarrow\s*\{\}', '\u2190', text)
    text = re.sub(r'\\textrightarrow\s*\{\}', '\u2192', text)
    # Non-braced tilde accent (Zotero emits e.g. {{\~X}} for spectroscopic
    # state labels); render as the letter with a combining tilde.
    text = re.sub(r'\\~\s*([A-Za-z])', '\\1\u0303', text)
    text = re.sub(r'\{([^{}]*)\}', r'\1', text)
    text = re.sub(r'\\relax\s?', '', text)
    text = text.replace('---', '\u2014')
    text = text.replace('--', '\u2013')
    text = text.replace(r'\&', '&')
    text = text.replace(r'\,', ' ')
    text = text.replace(r'\$', '$')
    text = text.replace(r'\_', '_')
    text = re.sub(r'\$(.+?)\$', r'\1', text)
    text = re.sub(r'\\[a-zA-Z]+(?:\{[^{}]*\})?', '', text)
    text = text.replace('{', '').replace('}', '')
    return text.strip()


# ── Author formatting ───────────────────────────────────────────────────────

def get_initials(first_name):
    parts = first_name.split()
    initials = []
    for p in parts:
        p = p.strip('.')
        if not p or not p[0].isalpha():
            continue
        sub = p.split('-')
        sub_init = [s[0].upper() + '.' for s in sub if s]
        initials.append('-'.join(sub_init))
    return ' '.join(initials)


def format_authors(author_str):
    if not author_str:
        return ''
    authors = [a.strip() for a in author_str.split(' and ')]
    formatted = []
    for author in authors:
        if ',' in author:
            last, first = author.split(',', 1)
            last = last.strip()
            first = first.strip()
        else:
            last = author
            first = ''
        initials = get_initials(first)
        formatted_name = f'{initials} {last}' if initials else last
        formatted.append(formatted_name)
    if len(formatted) == 1:
        result = formatted[0]
    elif len(formatted) == 2:
        result = f'{formatted[0]} & {formatted[1]}'
    else:
        result = ', '.join(formatted[:-1]) + ' & ' + formatted[-1]
    return result + '.'


# ── Citation formatting ─────────────────────────────────────────────────────

def format_citation(entry):
    journal = clean_latex(entry.get('journal', ''))
    volume = clean_latex(entry.get('volume', ''))
    pages = clean_latex(entry.get('pages', ''))
    year = entry.get('year', '')

    if not journal and volume and volume.lower().startswith('arxiv'):
        return f'<em>arXiv</em> {volume} ({year}).'

    if not journal:
        return f'({year}).' if year else '.'

    parts = [f'<em>{journal}</em>']
    if volume and not volume.lower().startswith('arxiv'):
        parts.append(f'<strong>{volume}</strong>')

    result = ' '.join(parts)
    if pages:
        result += f', {pages}'
    if year:
        result += f' ({year})'
    return result + '.'


def get_doi(entry):
    return clean_latex(entry.get('doi', '')).strip()


def get_entry_url(entry):
    doi = get_doi(entry)
    if doi:
        return f'https://doi.org/{doi}'
    volume = entry.get('volume', '')
    if volume and volume.lower().startswith('arxiv:'):
        arxiv_id = volume.split(':', 1)[1].strip()
        return f'https://arxiv.org/abs/{arxiv_id}'
    return '#'


def get_sort_key(entry):
    y = entry.get('year', '0')
    try:
        y = int(y)
    except ValueError:
        y = 0
    m = entry.get('month', '').strip().lower()[:3]
    m = MONTH_MAP.get(m, 0)
    return (-y, -m, entry.get('ID', ''))


# ── Selection storage ───────────────────────────────────────────────────────

def load_selections():
    if not SELECTION_FILE.exists():
        return {}
    try:
        data = json.loads(SELECTION_FILE.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {k: True for k in data}
    except (json.JSONDecodeError, Exception):
        pass
    return {}


def save_selections(selections):
    SELECTION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SELECTION_FILE.write_text(
        json.dumps(selections, indent=2, ensure_ascii=False) + '\n',
        encoding='utf-8'
    )


def is_selected(entry, selections):
    eid = entry.get('ID', '')
    if selections.get(eid, False):
        return True
    doi = get_doi(entry)
    if doi and selections.get(f'doi:{doi}', False):
        return True
    return False


def find_entry_by_ref(entries, ref):
    for e in entries:
        if e.get('ID', '') == ref:
            return e
        doi = get_doi(e)
        if doi and (doi == ref or f'doi:{doi}' == ref):
            return e
    return None


# ── HTML generation ─────────────────────────────────────────────────────────

def generate_pubs_html(entries, selections):
    total = len(entries)
    blocks = []
    for i, entry in enumerate(entries):
        year = clean_latex(str(entry.get('year', '')))
        title = clean_latex(entry.get('title', ''))
        author_raw = clean_latex(entry.get('author', ''))
        authors_html = format_authors(author_raw)
        citation_html = format_citation(entry)
        url = get_entry_url(entry)
        sel = 'true' if is_selected(entry, selections) else 'false'

        blocks.append(f"""        <div class="pub" data-selected="{sel}" data-date="{year}">
          <div class="pub-title"><span class="pub-year">{year}</span>{title}</div>
          <div class="pub-authors">{authors_html}</div>
          <div class="pub-journal">{citation_html}</div>
          <div class="pub-links">
            <a class="pub-link" href="{url}" target="_blank">View Paper</a>
          </div>
        </div>""")
    return '\n'.join(blocks)


def update_html_file(pubs_html):
    if not HTML_FILE.exists():
        die(f"{HTML_FILE} not found")

    content = HTML_FILE.read_text(encoding='utf-8')
    pattern = re.compile(
        r'(<!-- PUBLICATIONS_START -->).*?(<!-- PUBLICATIONS_END -->)',
        re.DOTALL
    )
    if not pattern.search(content):
        die(f"Markers not found in {HTML_FILE}")

    new_content = pattern.sub(
        rf'\g<1>\n{pubs_html}\n        \g<2>',
        content
    )
    HTML_FILE.write_text(new_content, encoding='utf-8')


# ── Display ─────────────────────────────────────────────────────────────────

def display_entry(entry, idx, total, is_sel):
    year = entry.get('year', '????')
    title = clean_latex(entry.get('title', ''))
    eid = entry.get('ID', '')
    doi = get_doi(entry) or '-'
    marker = '[*]' if is_sel else '[ ]'
    short_title = title[:80] + '...' if len(title) > 83 else title
    print(f"  {marker} {eid}")
    print(f"        {short_title}")
    print(f"        ({year}) doi: {doi}")
    print()


# ── Commands ────────────────────────────────────────────────────────────────

def cmd_list(args, entries, selections):
    selected_only = args.selected
    count = 0
    for i, entry in enumerate(entries):
        is_sel = is_selected(entry, selections)
        if selected_only and not is_sel:
            continue
        display_entry(entry, i, len(entries), is_sel)
        count += 1

    total_sel = sum(1 for e in entries if is_selected(e, selections))
    print(f"{'Selected' if selected_only else 'Total'}: {count} publication(s)")
    if not selected_only:
        print(f"Selected: {total_sel} publication(s)")


def cmd_select(args, entries, selections):
    ref = args.ref
    entry = find_entry_by_ref(entries, ref)
    if not entry:
        die(f"Publication not found: {ref}")
    eid = entry.get('ID', '')
    selections[eid] = True
    save_selections(selections)
    title = clean_latex(entry.get('title', ''))
    print(f"Selected: {eid} — {title[:60]}")


def cmd_deselect(args, entries, selections):
    ref = args.ref
    entry = find_entry_by_ref(entries, ref)
    if not entry:
        die(f"Publication not found: {ref}")
    eid = entry.get('ID', '')
    if eid in selections:
        del selections[eid]
    save_selections(selections)
    title = clean_latex(entry.get('title', ''))
    print(f"Deselected: {eid} — {title[:60]}")


def cmd_toggle(args, entries, selections):
    ref = args.ref
    entry = find_entry_by_ref(entries, ref)
    if not entry:
        die(f"Publication not found: {ref}")
    eid = entry.get('ID', '')
    is_sel = is_selected(entry, selections)
    if is_sel:
        if eid in selections:
            del selections[eid]
    else:
        selections[eid] = True
    save_selections(selections)
    title = clean_latex(entry.get('title', ''))
    status = 'Selected' if not is_sel else 'Deselected'
    print(f"{status}: {eid} — {title[:60]}")


def cmd_generate(args, entries, selections):
    entries.sort(key=get_sort_key)
    pubs_html = generate_pubs_html(entries, selections)
    update_html_file(pubs_html)
    total_sel = sum(1 for e in entries if is_selected(e, selections))
    print(f"Generated {HTML_FILE} with {len(entries)} publications ({total_sel} selected).")


def cmd_interactive(args, entries, selections):
    entries.sort(key=get_sort_key)

    while True:
        print("\n── Publications Manager ──────────────────────────────")
        print("Commands: [N]ext page  [P]rev page  [T]# toggle  [S]earch  [Q]uit")
        print("          select <id>  deselect <id>  generate")
        print("────────────────────────────────────────────────────")

        page_size = 15
        current_page = 0
        total_pages = (len(entries) + page_size - 1) // page_size

        while True:
            start = current_page * page_size
            end = min(start + page_size, len(entries))
            print(f"\nPage {current_page + 1}/{total_pages}")
            for i in range(start, end):
                entry = entries[i]
                is_sel = is_selected(entry, selections)
                marker = '[*]' if is_sel else '[ ]'
                eid = entry.get('ID', '')
                year = entry.get('year', '????')
                title = clean_latex(entry.get('title', ''))
                short = title[:72] + '...' if len(title) > 75 else title
                print(f"  {marker} {i+1:>2}. {eid:30s} ({year}) {short}")

            print()
            cmd = input("> ").strip()
            if not cmd:
                continue
            if cmd.lower() in ('q', 'quit', 'exit'):
                return
            if cmd.lower() in ('n', 'next'):
                current_page = (current_page + 1) % total_pages
                continue
            if cmd.lower() in ('p', 'prev', 'previous'):
                current_page = (current_page - 1) % total_pages
                continue
            if cmd.lower() == 'generate':
                pubs_html = generate_pubs_html(entries, selections)
                update_html_file(pubs_html)
                total_sel = sum(1 for e in entries if is_selected(e, selections))
                print(f"Generated {HTML_FILE} with {len(entries)} publications ({total_sel} selected).")
                continue

            if cmd.lower().startswith('t'):
                try:
                    idx = int(cmd[1:].strip()) - 1
                    if 0 <= idx < len(entries):
                        entry = entries[idx]
                        eid = entry.get('ID', '')
                        if is_selected(entry, selections):
                            if eid in selections:
                                del selections[eid]
                            print(f"  Deselected {eid}")
                        else:
                            selections[eid] = True
                            print(f"  Selected {eid}")
                        save_selections(selections)
                    else:
                        print("  Invalid index")
                except (ValueError, IndexError):
                    print("  Usage: t<number> (e.g., t3 to toggle #3)")
                continue

            if cmd.lower().startswith('select '):
                ref = cmd[7:].strip()
                entry = find_entry_by_ref(entries, ref)
                if entry:
                    eid = entry.get('ID', '')
                    selections[eid] = True
                    save_selections(selections)
                    print(f"  Selected {eid}")
                else:
                    print(f"  Not found: {ref}")
                continue

            if cmd.lower().startswith('deselect '):
                ref = cmd[9:].strip()
                entry = find_entry_by_ref(entries, ref)
                if entry:
                    eid = entry.get('ID', '')
                    if eid in selections:
                        del selections[eid]
                    save_selections(selections)
                    print(f"  Deselected {eid}")
                else:
                    print(f"  Not found: {ref}")
                continue

            if cmd.lower().startswith('search ') or cmd.lower() == 's':
                query = cmd[7:].strip().lower() if cmd.lower().startswith('search ') else ''
                if not query:
                    query = input("  Search: ").strip().lower()
                if query:
                    found = False
                    for i, entry in enumerate(entries):
                        title = clean_latex(entry.get('title', '')).lower()
                        eid = entry.get('ID', '').lower()
                        if query in title or query in eid:
                            if not found:
                                print(f"\n  Results for '{query}':")
                                found = True
                            is_sel = is_selected(entry, selections)
                            display_entry(entry, i, len(entries), is_sel)
                    if not found:
                        print(f"  No results for '{query}'")
                continue

            print(f"  Unknown command: {cmd}")


# ── PyQt6 GUI ──────────────────────────────────────────────────────────────

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QPushButton, QCheckBox, QListWidget,
        QListWidgetItem, QSplitter, QFrame, QMessageBox, QStatusBar,
        QTextEdit, QGroupBox, QAbstractItemView
    )
    from PyQt6.QtCore import Qt, QTimer
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False


def make_gui(entries, selections):
    if not HAS_PYQT6:
        die("PyQt6 is required for the GUI. Install with: pip install PyQt6")
    app = QApplication(sys.argv)
    window = ManagePublicationsGUI(entries, selections)
    window.show()
    sys.exit(app.exec())


class PublicationItem:
    def __init__(self, entry, selected):
        self.entry = entry
        self.selected = selected
        self.filter_visible = True


class ManagePublicationsGUI(QMainWindow):
    def __init__(self, entries, selections):
        super().__init__()
        self.entries = sorted(entries, key=get_sort_key)
        self.selections = selections

        self.items = []
        for e in self.entries:
            self.items.append(PublicationItem(e, is_selected(e, selections)))

        self.setWindowTitle("Manage Publications")
        self.setMinimumSize(1000, 650)
        self._build_ui()
        self._populate_list()
        self._update_status()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        # Top bar: search + filter toggle + generate
        top = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search titles or BibTeX keys...")
        self.search_input.textChanged.connect(self._filter_list)
        top.addWidget(self.search_input, 1)

        self.filter_btn = QPushButton("Show All")
        self.filter_btn.setFixedWidth(120)
        self.filter_btn.setCheckable(True)
        self.filter_btn.clicked.connect(self._toggle_filter)
        top.addWidget(self.filter_btn)

        self.generate_btn = QPushButton("Generate HTML")
        self.generate_btn.setFixedWidth(140)
        self.generate_btn.clicked.connect(self._generate)
        top.addWidget(self.generate_btn)
        layout.addLayout(top)

        # Splitter: list | detail
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: publication list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 4, 4, 0)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.currentRowChanged.connect(self._show_detail)
        left_layout.addWidget(self.list_widget)
        splitter.addWidget(left_panel)

        # Right: detail panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 0, 0)

        detail_group = QGroupBox("Publication Details")
        detail_layout = QVBoxLayout(detail_group)

        self.detail_id_label = QLabel()
        self.detail_id_label.setWordWrap(True)
        self.detail_id_label.setStyleSheet("font-weight: bold; color: #555;")
        detail_layout.addWidget(self.detail_id_label)

        self.detail_title = QLabel()
        self.detail_title.setWordWrap(True)
        self.detail_title.setStyleSheet("font-size: 15px; font-weight: 600;")
        detail_layout.addWidget(self.detail_title)

        self.detail_authors = QLabel()
        self.detail_authors.setWordWrap(True)
        self.detail_authors.setStyleSheet("color: #666;")
        detail_layout.addWidget(self.detail_authors)

        self.detail_journal = QLabel()
        self.detail_journal.setWordWrap(True)
        self.detail_journal.setStyleSheet("color: #888; font-style: italic;")
        detail_layout.addWidget(self.detail_journal)

        self.detail_doi = QLabel()
        self.detail_doi.setWordWrap(True)
        self.detail_doi.setStyleSheet("color: #3377cc;")
        detail_layout.addWidget(self.detail_doi)

        detail_layout.addStretch()

        self.sel_checkbox = QCheckBox("Selected (shown on homepage)")
        self.sel_checkbox.toggled.connect(self._toggle_selected)
        detail_layout.addWidget(self.sel_checkbox)

        right_layout.addWidget(detail_group)
        right_layout.addStretch()
        splitter.addWidget(right_panel)

        splitter.setSizes([550, 450])
        layout.addWidget(splitter, 1)

        # Status bar
        self.status_label = QLabel()
        self.statusBar().addPermanentWidget(self.status_label)

    def _populate_list(self, filter_text=""):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        filter_lower = filter_text.lower()
        for item in self.items:
            title = clean_latex(item.entry.get('title', '')).lower()
            eid = item.entry.get('ID', '').lower()
            visible = not filter_lower or filter_lower in title or filter_lower in eid
            item.filter_visible = visible
            if not visible:
                continue
            marker = '●' if item.selected else '○'
            year = item.entry.get('year', '????')
            short = clean_latex(item.entry.get('title', ''))
            if len(short) > 90:
                short = short[:87] + '...'
            display = f"{marker} [{year}] {short}"
            li = QListWidgetItem(display)
            li.setData(Qt.ItemDataRole.UserRole, self.items.index(item))
            if item.selected:
                li.setForeground(Qt.GlobalColor.darkBlue)
            self.list_widget.addItem(li)
        self.list_widget.blockSignals(False)

    def _filter_list(self):
        self._populate_list(self.search_input.text())
        self._update_status()

    def _toggle_filter(self):
        if self.filter_btn.isChecked():
            self.filter_btn.setText("Selected Only")
            self.list_widget.blockSignals(True)
            for i in range(self.list_widget.count()):
                li = self.list_widget.item(i)
                idx = li.data(Qt.ItemDataRole.UserRole)
                item = self.items[idx]
                li.setHidden(not item.selected)
            self.list_widget.blockSignals(False)
        else:
            self.filter_btn.setText("Show All")
            self._populate_list(self.search_input.text())
        self._update_status()

    def _show_detail(self, row):
        if row < 0:
            self._clear_detail()
            return
        li = self.list_widget.item(row)
        if not li:
            self._clear_detail()
            return
        idx = li.data(Qt.ItemDataRole.UserRole)
        item = self.items[idx]
        entry = item.entry

        self.detail_id_label.setText(f"ID: {entry.get('ID', '')}")
        self.detail_title.setText(clean_latex(entry.get('title', '')))
        self.detail_authors.setText(format_authors(clean_latex(entry.get('author', ''))))
        self.detail_journal.setText(format_citation(entry))
        doi = get_doi(entry) or '—'
        self.detail_doi.setText(f"DOI: {doi}")

        self.sel_checkbox.blockSignals(True)
        self.sel_checkbox.setChecked(item.selected)
        self.sel_checkbox.blockSignals(False)

    def _clear_detail(self):
        self.detail_id_label.setText("")
        self.detail_title.setText("")
        self.detail_authors.setText("")
        self.detail_journal.setText("")
        self.detail_doi.setText("")
        self.sel_checkbox.blockSignals(True)
        self.sel_checkbox.setChecked(False)
        self.sel_checkbox.blockSignals(False)

    def _toggle_selected(self, checked):
        row = self.list_widget.currentRow()
        if row < 0:
            return
        li = self.list_widget.item(row)
        idx = li.data(Qt.ItemDataRole.UserRole)
        item = self.items[idx]

        item.selected = checked
        eid = item.entry.get('ID', '')
        if checked:
            self.selections[eid] = True
        else:
            self.selections.pop(eid, None)
        save_selections(self.selections)

        self._populate_list(self.search_input.text())
        self._update_status()

        # Re-select same item after repopulate
        for i in range(self.list_widget.count()):
            li2 = self.list_widget.item(i)
            if li2.data(Qt.ItemDataRole.UserRole) == idx:
                self.list_widget.setCurrentRow(i)
                break

    def _update_status(self):
        total = len(self.items)
        sel = sum(1 for it in self.items if it.selected)
        vis = sum(1 for it in self.items if it.filter_visible)
        self.status_label.setText(f"Selected: {sel} / Visible: {vis} / Total: {total}")

    def _generate(self):
        entries_sorted = sorted(self.entries, key=get_sort_key)
        pubs_html = generate_pubs_html(entries_sorted, self.selections)
        update_html_file(pubs_html)
        total_sel = sum(1 for it in self.items if it.selected)
        save_selections(self.selections)

        msg = f"Generated {HTML_FILE} with {len(entries_sorted)} publications ({total_sel} selected)."

        try:
            subprocess.run(
                ["git", "add", str(HTML_FILE), str(SELECTION_FILE)],
                check=True, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30
            )
            subprocess.run(
                ["git", "commit", "-m", f"Update publications ({total_sel} selected)"],
                check=True, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30
            )
            msg += "\nCommitted locally."
            try:
                subprocess.run(
                    ["git", "push"],
                    check=True, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30
                )
                msg += "\nPushed to GitHub."
            except subprocess.CalledProcessError as e:
                msg += "\n\nCommit succeeded, but push to GitHub failed.\n\nTo push manually:\n  git push"
                QMessageBox.warning(
                    self, "Push Failed",
                    f"Commit succeeded, but pushing to GitHub failed.\n\nError: {e}\n\n"
                    "To push manually, run:\n  git push"
                )
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip()
            if "nothing to commit" in stderr:
                msg += "\nNo changes to commit."
            else:
                msg += f"\n\nGit error: {stderr}"

        QMessageBox.information(self, "Done", msg)
        self._update_status()


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Manage publications from publications.bib and generate publications.html. Run without arguments to open the GUI.'
    )
    subparsers = parser.add_subparsers(dest='command')

    p_list = subparsers.add_parser('list', help='List publications')
    p_list.add_argument('--selected', action='store_true', help='Show only selected publications')

    for cmd_name in ('select', 'deselect', 'toggle'):
        p = subparsers.add_parser(cmd_name, help=f'{cmd_name} a publication')
        p.add_argument('ref', help='BibTeX key or DOI')

    subparsers.add_parser('generate', help='Generate publications.html from .bib')
    subparsers.add_parser('interactive', help='Interactive selection mode')
    subparsers.add_parser('gui', help='Launch PyQt6 GUI')

    args = parser.parse_args()

    # No subcommand → open GUI
    if args.command is None:
        if not HAS_PYQT6:
            die("PyQt6 is required for the GUI. Install with: pip install PyQt6")
        if not BIB_FILE.exists():
            die(f"{BIB_FILE} not found")
        entries = parse_bib(BIB_FILE)
        seen = set()
        unique = []
        for e in entries:
            if e['ID'] not in seen:
                seen.add(e['ID'])
                unique.append(e)
        selections = load_selections()
        make_gui(unique, selections)
        return

    if args.command == 'gui':
        if not HAS_PYQT6:
            die("PyQt6 is required for the GUI. Install with: pip install PyQt6")
        entries = parse_bib(BIB_FILE)
        seen = set()
        unique = []
        for e in entries:
            if e['ID'] not in seen:
                seen.add(e['ID'])
                unique.append(e)
        selections = load_selections()
        make_gui(unique, selections)
        return

    if not BIB_FILE.exists():
        die(f"{BIB_FILE} not found")

    entries = parse_bib(BIB_FILE)

    seen = set()
    unique = []
    for e in entries:
        if e['ID'] not in seen:
            seen.add(e['ID'])
            unique.append(e)
    entries = unique

    selections = load_selections()

    if args.command == 'list':
        cmd_list(args, entries, selections)
    elif args.command == 'select':
        cmd_select(args, entries, selections)
    elif args.command == 'deselect':
        cmd_deselect(args, entries, selections)
    elif args.command == 'toggle':
        cmd_toggle(args, entries, selections)
    elif args.command == 'generate':
        cmd_generate(args, entries, selections)
    elif args.command == 'interactive':
        cmd_interactive(args, entries, selections)


if __name__ == '__main__':
    main()
