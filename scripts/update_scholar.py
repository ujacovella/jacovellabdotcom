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

            title   = bib.get('title', 'Unknown Title')
            authors = bib.get('author', 'Unknown Authors').replace(' and ', ', ')
            journal = bib.get('journal', '') or bib.get('citation', '')
            pub_url = pub.get('pub_url', '#')

            parsed.append({
                'year':    year,
                'pub_year': bib.get('pub_year', ''),
                'title':   title,
                'authors': authors,
                'journal': journal,
                'pub_url': pub_url,
            })
            print(f"{ts()} [{i}/{len(raw_pubs)}] {year}  {title[:70]}")
        except Exception as e:
            print(f"{ts()} WARNING — Skipping publication {i}: {e}")

    if not parsed:
        print(f"{ts()} ERROR — No publications could be parsed.")
        return None

    # ── Sort by year descending (most recent first) ──
    parsed.sort(key=lambda p: p['year'], reverse=True)
    print(f"{ts()} Sorted {len(parsed)} publications by year, newest first.")

    html_content = ""
    for p in parsed:
        html_content += f"""
        <div class="pub">
          <div class="pub-title"><span class="pub-year">{p['pub_year']}</span>{p['title']}</div>
          <div class="pub-authors">{p['authors']}</div>
          <div class="pub-journal"><em>{p['journal']}</em></div>
          <div class="pub-links">
            <a class="pub-link" href="{p['pub_url']}" target="_blank">View Paper</a>
          </div>
        </div>"""

    return html_content

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

    pubs_html = fetch_publications()
    if pubs_html:
        update_html(pubs_html)
    else:
        print(f"{ts()} Aborted — nothing written to {HTML_FILE}.")
