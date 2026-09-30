import glob
import os
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')

os.makedirs('images', exist_ok=True)

files = sorted(glob.glob('raw_html/*.html'))

image_urls = {}

for f in files:
    bn = os.path.basename(f).replace('.html', '')
    parts = bn.split('_') # e.g. 2022, S1, Quant
    yr = parts[0]
    slot = parts[1].replace('S', '')
    sec = parts[2]
    
    paper_url = f"https://online.2iim.com/CAT-question-paper/CAT-{yr}-Question-Paper-Slot-{slot}-{sec}/"
    
    with open(f, 'r', encoding='utf-8') as fp:
        html = fp.read()
    
    soup = BeautifulSoup(html, 'lxml')
    
    for img in soup.find_all('img'):
        src = img.get('src')
        if not src:
            continue
        # Filter out site chrome/logos/ads
        src_lower = src.lower()
        if any(x in src_lower for x in [
            '2iim-logo', 'logo', 'icon', 'loading', 'popup', 'offer', 'amazon', 
            'sponsor', 'welingkar', 'joey-results', 'wizako', 'piverb', 'facebook',
            'twitter', 'youtube', 'whatsapp', 'quora', 'svgs', 'touch'
        ]):
            continue
            
        full_src = urljoin(paper_url, src)
        # determine local filename
        clean_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', os.path.basename(src.split('?')[0]))
        local_name = f"{yr}_{parts[1]}_{sec}_{clean_name}"
        image_urls[full_src] = local_name

print(f"Total unique question images found across papers: {len(image_urls)}")
for url, loc in list(image_urls.items())[:15]:
    print(f"{loc} <-- {url}")
