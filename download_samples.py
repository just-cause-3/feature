import os
import requests
from bs4 import BeautifulSoup
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

os.makedirs('raw_html', exist_ok=True)

test_papers = [
    (2017, 1, 'Quant'),
    (2017, 1, 'DILR'),
    (2017, 1, 'VARC'),
    (2018, 1, 'Quant'),
    (2018, 1, 'DILR'),
    (2018, 1, 'VARC'),
    (2019, 1, 'Quant'),
    (2019, 1, 'DILR'),
    (2019, 1, 'VARC'),
    (2020, 1, 'Quant'),
    (2020, 1, 'DILR'),
    (2020, 1, 'VARC'),
    (2021, 1, 'Quant'),
    (2021, 1, 'DILR'),
    (2021, 1, 'VARC'),
    (2022, 1, 'Quant'),
    (2022, 1, 'DILR'),
    (2022, 1, 'VARC'),
]

base_url = 'https://online.2iim.com/CAT-question-paper/'

for yr, slot, sec in test_papers:
    fname = f"raw_html/{yr}_S{slot}_{sec}.html"
    if not os.path.exists(fname):
        url = f"{base_url}CAT-{yr}-Question-Paper-Slot-{slot}-{sec}/"
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
            r.encoding = 'utf-8'
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(r.text)
            print(f"Downloaded {fname}")
        except Exception as e:
            print(f"Failed {url}: {e}")

print("All sample papers downloaded.")
