import os
import re
import time
from datetime import datetime, timezone
from scholarly import scholarly, ProxyGenerator

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
AUTHOR_ID  = 'bvbpeyUAAAAJ'   # Google Scholar author ID (from the URL ?user=...)
HTML_FILE  = 'publications.html'
MAX_RETRIES = 3                # Retries per publication fill
USE_PROXY   = True             # Set to False to skip proxy (faster but more likely blocked)
# ──────────────────────────────────────────────────────────────────────────────

def ts():
    """Return a formatted UTC timestamp string."""
    return datetime.now(timezone.utc).strftime('[%Y-%m-%d %H:%M:%S UTC]')

def setup_proxy():
    """Try to configure a free proxy to avoid Google Scholar blocks."""
    if not USE_PROXY:
        return
    print(f"{ts()} Setting up free proxy pool...")
    try:
        pg = ProxyGenerator()
        pg.FreeProxies()
        scholarly.use_proxy(pg)
        print(f"{ts()} Proxy pool ready.")
    except Exception as e:
        print(f"{ts()} WARNING — Could not set up proxy ({e}). Proceeding without proxy.")

def fill_with_retry(pub, retries=MAX_RETRIES):
    """Fill a publication stub with retries and back-off."""
    for attempt in range(1, retries + 1):
        try:
            return scholarly.fill(pub)
        except Exception as e:
            if attempt < retries:
                wait = 5 * attempt
                print(f"{ts()} WARNING — Fill attempt {attempt} failed ({e}). Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

def fetch_publications(selected_states=None, manual_entries=None):
    if selected_states is None: selected_states = {}
    if manual_entries is None: manual_entries = []

    print(f"{ts()} Fetching author profile for Scholar ID: {AUTHOR_ID}")
    setup_proxy()

    # Fetch the author profile
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            author = scholarly.search_author_id(AUTHOR_ID)
            # NOTE: sortby on fill() affects which Scholar tab is scraped.
            # We do our own sort after filling, so this is just a hint.
            author = scholarly.fill(author, sections=['publications'], sortby='year')
            break
        except Exception as e:
            if attempt < MAX_RETRIES:
                wait = 10 * attempt
                print(f"{ts()} WARNING — Author fetch attempt {attempt} failed ({e}). Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"{ts()} ERROR — Failed to fetch author after {MAX_RETRIES} attempts: {e}")
                return None

    raw_pubs = author.get('publications', [])
    print(f"{ts()} Found {len(raw_pubs)} publications. Filling details...")

    parsed = []
    for i, pub in enumerate(raw_pubs, 1):
        try:
            pub = fill_with_retry(pub)
            bib = pub.get('bib', {})

            try:
                year = int(bib.get('pub_year', 0))
            except (ValueError, TypeError):
                year = 0

            # Build a full sortable date: prefer pub_date (can be 'YYYY/MM/DD'),
            # fall back to pub_year only.
            raw_date = str(bib.get('pub_date', '') or bib.get('pub_year', ''))
            # Normalise YYYY/MM/DD  or  YYYY/MM  or  YYYY  → YYYY-MM-DD
            parts = [p.zfill(2) for p in raw_date.replace('/', '-').split('-')]
            if len(parts) == 3:
                sort_date = '-'.join(parts)          # YYYY-MM-DD
            elif len(parts) == 2:
                sort_date = f"{parts[0]}-{parts[1]}-00"
            elif len(parts) == 1 and parts[0]:
                sort_date = f"{parts[0]}-00-00"
            else:
                sort_date = '0000-00-00'

            title   = str(bib.get('title', 'Unknown Title'))
            authors = str(bib.get('author', 'Unknown Authors')).replace(' and ', ', ')
            journal = bib.get('journal', '') or bib.get('citation', '')
            pub_url = pub.get('pub_url', '#')

            parsed.append({
                'sort_date': sort_date,
                'year':      year,
                'pub_year':  bib.get('pub_year', ''),
                'title':     title,
                'authors':   authors,
                'journal':   journal,
                'pub_url':   pub_url,
            })
            print(f"{ts()} [{i}/{len(raw_pubs)}] {sort_date}  {title[:70]}")
        except Exception as e:
            print(f"{ts()} WARNING — Skipping publication {i}: {e}")

    # ── Merge manual entries ──
    if manual_entries:
        parsed.extend(manual_entries)
        print(f"{ts()} Merged {len(manual_entries)} manual entries.")

    if not parsed:
        print(f"{ts()} ERROR — No publications could be parsed.")
        return None

    # ── Sort by full date descending (most recent first) ──
    parsed.sort(key=lambda p: p['sort_date'], reverse=True)
    total_pubs = len(parsed)
    print(f"{ts()} Sorted {total_pubs} publications by date, newest first.")

    html_content = ""
    for i, p in enumerate(parsed):
        # Determine selected state (prefer manual value, else look up in states)
        is_manual = p.get('manual', False)
        if is_manual:
            sel_val = p.get('selected', 'false')
            manual_attr = ' data-manual="true"'
        else:
            sel_val = selected_states.get(p['pub_url'], 'false')
            manual_attr = ''

        pub_num = total_pubs - i
        html_content += f"""
        <div class="pub" data-selected="{sel_val}"{manual_attr} data-date="{p['sort_date']}" data-num="{pub_num}">
          <div class="pub-title"><span class="pub-year">{p['pub_year']}</span>{p['title']}</div>
          <div class="pub-authors">{p['authors']}</div>
          <div class="pub-journal"><em>{p['journal']}</em></div>
          <div class="pub-links">
            <a class="pub-link" href="{p['pub_url']}" target="_blank">View Paper</a>
          </div>
        </div>"""

    return html_content

def load_existing_data(html_file):
    """Read existing data from publications.html.
    Returns: (selected_states, manual_entries)
    - selected_states: dict (url -> 'true'/'false')
    - manual_entries: list of dicts (parsed entry objects)
    """
    if not os.path.exists(html_file):
        return {}, []

    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    pub_re = re.compile(r'<div class="pub"([^>]*)>(.*?)</div>\s*</div>', re.DOTALL)
    url_re = re.compile(r'href="([^"]+)"')
    sel_re = re.compile(r'data-selected="(true|false)"')
    man_re = re.compile(r'data-manual="true"')
    date_re = re.compile(r'data-date="([^"]+)"')
    title_re = re.compile(r'<div class="pub-title"><span class="pub-year">([^<]*)</span>([^<]+)</div>')
    auth_re = re.compile(r'<div class="pub-authors">([^<]+)</div>')
    jour_re = re.compile(r'<div class="pub-journal"><em>([^<]*)</em></div>')

    states = {}
    manuals = []

    for m in pub_re.finditer(content):
        attrs, body = m.group(1), m.group(2)
        url_m = url_re.search(body)
        url = url_m.group(1).strip() if url_m else '#'
        sel_m = sel_re.search(attrs)
        sel_val = sel_m.group(1) if sel_m else 'false'

        if man_re.search(attrs):
            date_m = date_re.search(attrs)
            tit_m = title_re.search(body)
            aut_m = auth_re.search(body)
            jou_m = jour_re.search(body)

            manuals.append({
                'sort_date': date_m.group(1) if date_m else '0000-00-00',
                'pub_year': tit_m.group(1) if tit_m else '',
                'title': tit_m.group(2).strip() if tit_m else 'Unknown',
                'authors': aut_m.group(1).strip() if aut_m else 'Unknown',
                'journal': jou_m.group(1).strip() if jou_m else '',
                'pub_url': url,
                'selected': sel_val,
                'manual': True
            })
        else:
            if url != '#':
                states[url] = sel_val

    sel_count = sum(1 for v in states.values() if v == 'true') + sum(1 for m in manuals if m['selected'] == 'true')
    print(f"{ts()} Loaded {len(states)} Scholar states and {len(manuals)} manual entries ({sel_count} total selected).")
    return states, manuals

def update_html(publications_html):
    if not os.path.exists(HTML_FILE):
        print(f"{ts()} ERROR — {HTML_FILE} not found.")
        return False

    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = re.compile(
        r'(<!-- PUBLICATIONS_START -->)(.*?)(<!-- PUBLICATIONS_END -->)',
        re.DOTALL
    )

    if not pattern.search(content):
        print(f"{ts()} ERROR — Marker comments not found in {HTML_FILE}.")
        return False

    new_content = pattern.sub(rf'\g<1>\n{publications_html}\n        \g<3>', content)

    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"{ts()} Successfully wrote {HTML_FILE}.")
    return True

if __name__ == "__main__":
    # Ensure working directory is the repo root (script lives in scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root  = os.path.dirname(script_dir)
    os.chdir(repo_root)

    selected_states, manual_entries = load_existing_data(HTML_FILE)
    pubs_html = fetch_publications(selected_states, manual_entries)
    if pubs_html:
        update_html(pubs_html)
    else:
        print(f"{ts()} Aborted — nothing written to {HTML_FILE}.")
