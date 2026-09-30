import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

sys.stdout.reconfigure(encoding='utf-8')

os.makedirs('raw_html', exist_ok=True)

base_url = 'https://online.2iim.com/CAT-question-paper/'

papers = []
# 2017-2022 (and 2023-2024)
years_slots = {
    2017: [1, 2],
    2018: [1, 2],
    2019: [1, 2],
    2020: [1, 2, 3],
    2021: [1, 2, 3],
    2022: [1, 2, 3],
    2023: [1, 2, 3],
    2024: [1, 2, 3],
}

sections = ['Quant', 'DILR', 'VARC']

for yr, slots in years_slots.items():
    for slot in slots:
        for sec in sections:
            slug = f"CAT-{yr}-Question-Paper-Slot-{slot}-{sec}"
            url = f"{base_url}{slug}/"
            out_file = f"raw_html/{yr}_S{slot}_{sec}.html"
            papers.append({
                'year': yr,
                'slot': slot,
                'section': sec,
                'slug': slug,
                'url': url,
                'file': out_file
            })

def fetch_paper(p):
    if os.path.exists(p['file']) and os.path.getsize(p['file']) > 10000:
        return p['file'], True, "Cached"
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        r = requests.get(p['url'], headers=headers, timeout=25)
        if r.status_code == 200:
            r.encoding = 'utf-8'
            with open(p['file'], 'w', encoding='utf-8') as f:
                f.write(r.text)
            return p['file'], True, "Downloaded"
        else:
            return p['file'], False, f"Status {r.status_code}"
    except Exception as e:
        return p['file'], False, str(e)

print(f"Starting download of {len(papers)} papers...")
with ThreadPoolExecutor(max_workers=6) as executor:
    futures = {executor.submit(fetch_paper, p): p for p in papers}
    success_count = 0
    for future in as_completed(futures):
        f_name, ok, msg = future.result()
        if ok:
            success_count += 1
            print(f"[OK] {os.path.basename(f_name)}: {msg}")
        else:
            print(f"[FAILED] {os.path.basename(f_name)}: {msg}")

print(f"\nCompleted: {success_count}/{len(papers)} papers downloaded successfully.")
