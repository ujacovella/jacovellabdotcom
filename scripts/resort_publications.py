"""
resort_publications.py
Re-sorts the existing publications.html by year (newest first)
without making any network requests.
Run from the repo root: python3 scripts/resort_publications.py
"""
import re
import os

HTML_FILE = 'publications.html'

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root  = os.path.dirname(script_dir)
    os.chdir(repo_root)

    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract the block between the markers
    marker_re = re.compile(
        r'(<!-- PUBLICATIONS_START -->)(.*?)(<!-- PUBLICATIONS_END -->)',
        re.DOTALL
    )
    m = marker_re.search(content)
    if not m:
        print("ERROR: markers not found in", HTML_FILE)
        return

    pubs_block = m.group(2)

    # Split into individual <div class="pub"> entries
    pubs = [p.strip() for p in re.split(r'\s*(?=<div class="pub")', pubs_block) if p.strip()]
    print(f"Found {len(pubs)} publication entries.")

    # Extract sort key: prefer data-date="YYYY-MM-DD", fall back to <span class="pub-year">
    date_attr_re = re.compile(r'<div class="pub"[^>]*data-date="([^"]+)"')
    year_span_re = re.compile(r'<span class="pub-year">([^<]*)</span>')

    def get_sort_key(pub_html):
        # Try data-date first (full YYYY-MM-DD)
        dm = date_attr_re.search(pub_html)
        if dm:
            return dm.group(1)
        # Fall back to year only
        ym = year_span_re.search(pub_html)
        if ym and ym.group(1).strip():
            return f"{ym.group(1).strip()}-00-00"
        return '0000-00-00'

    pubs_sorted = sorted(pubs, key=get_sort_key, reverse=True)

    # Show what changed
    keys_before = [get_sort_key(p) for p in pubs]
    keys_after  = [get_sort_key(p) for p in pubs_sorted]
    print(f"Sort key before: {keys_before[:6]}{'...' if len(keys_before) > 6 else ''}")
    print(f"Sort key after:  {keys_after[:6]}{'...' if len(keys_after) > 6 else ''}")

    new_block = '\n        ' + '\n        '.join(pubs_sorted) + '\n        '
    new_content = marker_re.sub(rf'\g<1>{new_block}\g<3>', content)

    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Done. {HTML_FILE} rewritten with {len(pubs_sorted)} publications sorted by year.")

if __name__ == '__main__':
    main()
