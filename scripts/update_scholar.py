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

def fetch_publications():
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
            raw_date = bib.get('pub_date', '') or bib.get('pub_year', '')
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

            title   = bib.get('title', 'Unknown Title')
            authors = bib.get('author', 'Unknown Authors').replace(' and ', ', ')
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

    if not parsed:
        print(f"{ts()} ERROR — No publications could be parsed.")
        return None

    # ── Sort by full date descending (most recent first) ──
    parsed.sort(key=lambda p: p['sort_date'], reverse=True)
    print(f"{ts()} Sorted {len(parsed)} publications by date, newest first.")

    html_content = ""
    for p in parsed:
        html_content += f"""
        <div class="pub" data-date="{p['sort_date']}">
          <div class="pub-title"><span class="pub-year">{p['pub_year']}</span>{p['title']}</div>
          <div class="pub-authors">{p['authors']}</div>
          <div class="pub-journal"><em>{p['journal']}</em></div>
          <div class="pub-links">
            <a class="pub-link" href="{p['pub_url']}" target="_blank">View Paper</a>
          </div>
        </div>"""

    return html_content

def load_selected_states(html_file):
    """Read data-selected values from existing publications.html.
    Returns a dict keyed by canonical pub URL -> 'true' or 'false'.
    """
    if not os.path.exists(html_file):
        return {}
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    # Match each pub block: capture attrs and inner HTML
    pub_re   = re.compile(r'<div class="pub"([^>]*)>(.*?)</div>\s*</div>', re.DOTALL)
    url_re   = re.compile(r'href="([^"]+)"')
    sel_re   = re.compile(r'data-selected="(true|false)"')
    states   = {}
    for m in pub_re.finditer(content):
        attrs, body = m.group(1), m.group(2)
        url_m = url_re.search(body)
        sel_m = sel_re.search(attrs)
        if url_m:
            url   = url_m.group(1).strip()
            value = sel_m.group(1) if sel_m else 'false'
            states[url] = value
    selected_count = sum(1 for v in states.values() if v == 'true')
    print(f"{ts()} Loaded {len(states)} existing selected states ({selected_count} marked true).")
    return states

def update_html(publications_html):
    if not os.path.exists(HTML_FILE):
        print(f"{ts()} ERROR — {HTML_FILE} not found.")
        return False

    # Preserve user-set data-selected values before overwriting
    selected_states = load_selected_states(HTML_FILE)

    # Apply preserved selected states to the new HTML
    if selected_states:
        def apply_selected(match):
            url = match.group(1)
            value = selected_states.get(url, 'false')
            return f'data-selected="{value}" href="{url}"'
        # Replace href="URL" inside pub blocks, carrying over the selected state
        publications_html = re.sub(
            r'data-selected="false" href="([^"]+)"',
            apply_selected,
            publications_html
        )

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

    pubs_html = fetch_publications()
    if pubs_html:
        update_html(pubs_html)
    else:
        print(f"{ts()} Aborted — nothing written to {HTML_FILE}.")
