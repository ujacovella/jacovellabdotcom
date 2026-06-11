"""
generate_publications.py
Parses assets/publications.bib and generates the publication list in publications.html.
Replaces the Google Scholar-based update system.

Citation style (matching the group's convention):
  Authors. Title. <em>Journal</em> <strong>Volume</strong>, Pages (Year).
"""

import os
import re
import sys
import subprocess

BIB_FILE = 'assets/publications.bib'
HTML_FILE = 'publications.html'

LATEX_ACCENT_COMMANDS = [
    # caron: \v{s}  (allow optional space before letter argument)
    (r'\{\\v\{([a-zA-Z])\}\}', lambda m: {'s':'š','S':'Š','z':'ž','Z':'Ž','c':'č','C':'Č','r':'ř','R':'Ř'}.get(m.group(1),m.group(1))),
    (r'\{\\v\s*([a-zA-Z])\}',   lambda m: {'s':'š','S':'Š','z':'ž','Z':'Ž','c':'č','C':'Č','r':'ř','R':'Ř'}.get(m.group(1),m.group(1))),
    # double acute: \H{o}
    (r'\{\\H\{([a-zA-Z])\}\}', lambda m: {'o':'ő','O':'Ő','u':'ű','U':'Ű'}.get(m.group(1),m.group(1))),
    (r'\{\\H\s*([a-zA-Z])\}',   lambda m: {'o':'ő','O':'Ő','u':'ű','U':'Ű'}.get(m.group(1),m.group(1))),
    # cedilla: \c{c}
    (r'\{\\c\{([a-zA-Z])\}\}', lambda m: {'c':'ç','C':'Ç'}.get(m.group(1),m.group(1))),
    (r'\{\\c\s*([a-zA-Z])\}',   lambda m: {'c':'ç','C':'Ç'}.get(m.group(1),m.group(1))),
    # acute: \'{e}
    (r"\{\\'\{([a-zA-Z])\}\}", lambda m: {'a':'á','e':'é','i':'í','o':'ó','u':'ú','y':'ý','c':'ć','n':'ń','A':'Á','E':'É','I':'Í','O':'Ó','U':'Ú','Y':'Ý','C':'Ć','N':'Ń'}.get(m.group(1),m.group(1))),
    (r"\{\\'\s*([a-zA-Z])\}",   lambda m: {'a':'á','e':'é','i':'í','o':'ó','u':'ú','y':'ý','c':'ć','n':'ń','A':'Á','E':'É','I':'Í','O':'Ó','U':'Ú','Y':'Ý','C':'Ć','N':'Ń'}.get(m.group(1),m.group(1))),
    # grave: \`{e}
    (r'\{\\`\{([a-zA-Z])\}\}', lambda m: {'a':'à','e':'è','i':'ì','o':'ò','u':'ù','A':'À','E':'È','I':'Ì','O':'Ò','U':'Ù'}.get(m.group(1),m.group(1))),
    (r'\{\\`\s*([a-zA-Z])\}',   lambda m: {'a':'à','e':'è','i':'ì','o':'ò','u':'ù','A':'À','E':'È','I':'Ì','O':'Ò','U':'Ù'}.get(m.group(1),m.group(1))),
    # circumflex: \^{e}
    (r'\{\\\^\{([a-zA-Z])\}\}', lambda m: {'a':'â','e':'ê','i':'î','o':'ô','u':'û','A':'Â','E':'Ê','I':'Î','O':'Ô','U':'Û'}.get(m.group(1),m.group(1))),
    (r'\{\\\^\s*([a-zA-Z])\}',   lambda m: {'a':'â','e':'ê','i':'î','o':'ô','u':'û','A':'Â','E':'Ê','I':'Î','O':'Ô','U':'Û'}.get(m.group(1),m.group(1))),
    # umlaut: \"{o}
    (r'\{\\"\{([a-zA-Z])\}\}', lambda m: {'a':'ä','e':'ë','i':'ï','o':'ö','u':'ü','A':'Ä','E':'Ë','I':'Ï','O':'Ö','U':'Ü'}.get(m.group(1),m.group(1))),
    (r'\{\\"\s*([a-zA-Z])\}',   lambda m: {'a':'ä','e':'ë','i':'ï','o':'ö','u':'ü','A':'Ä','E':'Ë','I':'Ï','O':'Ö','U':'Ü'}.get(m.group(1),m.group(1))),
    # tilde: \~{n}
    (r'\{\\\~\{([a-zA-Z])\}\}', lambda m: {'a':'ã','n':'ñ','o':'õ','A':'Ã','N':'Ñ','O':'Õ'}.get(m.group(1),m.group(1))),
    (r'\{\\\~\s*([a-zA-Z])\}',   lambda m: {'a':'ã','n':'ñ','o':'õ','A':'Ã','N':'Ñ','O':'Õ'}.get(m.group(1),m.group(1))),
]

MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ── BibTeX parser ──────────────────────────────────────────────────────────────

def parse_bib(filepath):
    """Parse a BibTeX file and return a list of entry dicts."""
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
        body = text[body_start:i-1]

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
                value = body[val_start+1:j-1]
                pos = j
            elif body[val_start] == '"':
                j = body.find('"', val_start + 1)
                value = body[val_start+1:j] if j != -1 else body[val_start+1:]
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


# ── LaTeX cleaning ─────────────────────────────────────────────────────────────

def clean_latex(text):
    """Convert LaTeX markup to plain text / HTML."""
    if not text:
        return ''

    # {{..}} → content (BibTeX case protection)
    text = re.sub(r'\{\{(.+?)\}\}', r'\1', text)

    for pattern, repl in LATEX_ACCENT_COMMANDS:
        text = re.sub(pattern, repl, text)

    # Remove remaining { } around plain content
    text = re.sub(r'\{([^{}]*)\}', r'\1', text)

    # \textsubscript / \textsuperscript
    text = re.sub(r'\\textsubscript\{([^{}]*)\}', r'<sub>\1</sub>', text)
    text = re.sub(r'\\textsuperscript\{([^{}]*)\}', r'<sup>\1</sup>', text)

    # \emph / \textit → content only
    text = re.sub(r'\\emph\{([^{}]*)\}', r'\1', text)
    text = re.sub(r'\\textit\{([^{}]*)\}', r'\1', text)

    # Arrows
    text = re.sub(r'\\textleftarrow\{\}', '\u2190', text)
    text = re.sub(r'\\textrightarrow\{\}', '\u2192', text)

    # \relax
    text = re.sub(r'\\relax\s?', '', text)

    # Dashes
    text = text.replace('---', '\u2014')
    text = text.replace('--', '\u2013')

    text = text.replace(r'\&', '&')
    text = text.replace(r'\,', ' ')

    # Escaped special chars (must happen before math-mode removal)
    text = text.replace(r'\$', '$')
    text = text.replace(r'\_', '_')

    # Math-mode delimiters: $...$ → content
    text = re.sub(r'\$(.+?)\$', r'\1', text)

    # Remove any remaining LaTeX commands
    text = re.sub(r'\\[a-zA-Z]+(?:\{[^{}]*\})?', '', text)

    text = text.replace('{', '').replace('}', '')

    return text.strip()


# ── Author formatting ──────────────────────────────────────────────────────────

def get_initials(first_name):
    """Convert first name to initials: 'Marie-Aline' → 'M.-A.'"""
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
    """Return 'C. Rossi, … & U. Jacovella.'"""
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

# ── Citation formatting ────────────────────────────────────────────────────────

def format_citation(entry):
    """Return '<em>Journal</em> <strong>Vol</strong>, Pages (Year).' """
    journal = clean_latex(entry.get('journal', ''))
    volume = clean_latex(entry.get('volume', ''))
    pages = clean_latex(entry.get('pages', ''))
    year = entry.get('year', '')

    # arXiv
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
    """Return a tuple for descending sort: (-year, -month, ID)."""
    y = entry.get('year', '0')
    try:
        y = int(y)
    except ValueError:
        y = 0

    m = entry.get('month', '').strip().lower()[:3]
    m = MONTH_MAP.get(m, 0)

    return (-y, -m, entry.get('ID', ''))


# ── HTML operations ────────────────────────────────────────────────────────────

def load_selected_states(html_file):
    """Read existing data-selected states from publications.html.

    Keys are (lowercased title) so we can match even when URLs change.
    Also stores DOI-based keys as a fallback.
    """
    if not os.path.exists(html_file):
        return {}

    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    states = {}

    pub_re = re.compile(
        r'<div class="pub"([^>]*)>(.*?)</div>\s*</div>',
        re.DOTALL
    )
    title_re = re.compile(
        r'<div class="pub-title"><span class="pub-year">[^<]*</span>(.*?)</div>',
        re.DOTALL
    )
    doi_re = re.compile(r'href="https://doi\.org/([^"]+)"')
    arxiv_re = re.compile(r'href="https://arxiv\.org/abs/([^"]+)"')

    for m in pub_re.finditer(content):
        attrs = m.group(1)
        body = m.group(2)

        sel_m = re.search(r'data-selected="(true|false)"', attrs)
        if not sel_m:
            continue
        sel_val = sel_m.group(1)
        if sel_val != 'true':
            continue

        # Key by title (lowercased, whitespace collapsed)
        tit_m = title_re.search(body)
        if tit_m:
            key = re.sub(r'\s+', ' ', tit_m.group(1)).strip().lower()
            states[key] = sel_val

        # Also store DOI-based keys
        doi_m = doi_re.search(body)
        if doi_m:
            states[doi_m.group(1)] = sel_val
        arxiv_m = arxiv_re.search(body)
        if arxiv_m:
            states['arxiv:' + arxiv_m.group(1)] = sel_val

    return states


def update_html(html_file, pubs_html):
    """Replace content between PUBLICATIONS_START / END markers."""
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = re.compile(
        r'(<!-- PUBLICATIONS_START -->).*?(<!-- PUBLICATIONS_END -->)',
        re.DOTALL
    )

    if not pattern.search(content):
        die(f"Markers not found in {html_file}")

    new_content = pattern.sub(
        rf'\g<1>\n{pubs_html}\n        \g<2>',
        content
    )

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(new_content)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    os.chdir(repo_root)

    if not os.path.exists(BIB_FILE):
        die(f"{BIB_FILE} not found")
    if not os.path.exists(HTML_FILE):
        die(f"{HTML_FILE} not found")

    print(f"Parsing {BIB_FILE} …")
    entries = parse_bib(BIB_FILE)

    # Deduplicate by ID
    seen = set()
    unique = []
    for e in entries:
        if e['ID'] not in seen:
            seen.add(e['ID'])
            unique.append(e)
    entries = unique
    print(f"  {len(entries)} entries")

    entries.sort(key=get_sort_key)

    states = load_selected_states(HTML_FILE)
    print(f"  {len(states)} saved selected states")

    total = len(entries)
    blocks = []

    for i, entry in enumerate(entries):
        year = clean_latex(str(entry.get('year', '')))
        title = clean_latex(entry.get('title', ''))

        author_raw = clean_latex(entry.get('author', ''))
        authors_html = format_authors(author_raw)

        citation_html = format_citation(entry)
        url = get_entry_url(entry)

        # Look up selected state
        doi = get_doi(entry)
        sel = 'false'
        if doi and doi in states:
            sel = states[doi]
        if sel == 'false':
            vol = entry.get('volume', '')
            if vol and vol.lower().startswith('arxiv:'):
                arxiv_id = vol.split(':', 1)[1].strip()
                sel = states.get('arxiv:' + arxiv_id, 'false')
        # Fallback: match by lowercased title (whitespace collapsed)
        if sel == 'false':
            title_key = re.sub(r'\s+', ' ', title).lower()
            sel = states.get(title_key, 'false')

        pub_num = total - i

        blocks.append(f"""        <div class="pub" data-selected="{sel}" data-date="{year}">
          <div class="pub-title"><span class="pub-year">{year}</span>{title}</div>
          <div class="pub-authors">{authors_html}</div>
          <div class="pub-journal">{citation_html}</div>
          <div class="pub-links">
            <a class="pub-link" href="{url}" target="_blank">View Paper</a>
          </div>
        </div>""")

    pubs_html = '\n'.join(blocks)

    print(f"Writing {total} publications to {HTML_FILE} …")
    update_html(HTML_FILE, pubs_html)
    print("Done.")

    try:
        subprocess.run(
            ["git", "add", HTML_FILE, BIB_FILE],
            check=True, cwd=repo_root, capture_output=True, text=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"Update publications page ({total} entries)"],
            check=True, cwd=repo_root, capture_output=True, text=True
        )
        subprocess.run(
            ["git", "push"],
            check=True, cwd=repo_root, capture_output=True, text=True
        )
        print("Committed and pushed to Git.")
    except Exception as e:
        print(f"Git: {e}")


if __name__ == '__main__':
    main()
