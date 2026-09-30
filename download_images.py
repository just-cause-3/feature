import os
import requests
from concurrent.futures import ThreadPoolExecutor
import sys

sys.stdout.reconfigure(encoding='utf-8')
from find_images import image_urls

os.makedirs('images', exist_ok=True)

def download_img(item):
    url, filename = item
    target_path = os.path.join('images', filename)
    if os.path.exists(target_path) and os.path.getsize(target_path) > 100:
        return filename, True, "Cached"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        if r.status_code == 200:
            with open(target_path, 'wb') as f:
                f.write(r.content)
            return filename, True, "Downloaded"
        else:
            return filename, False, f"Status {r.status_code}"
    except Exception as e:
        return filename, False, str(e)

print(f"Downloading {len(image_urls)} images...")
with ThreadPoolExecutor(max_workers=8) as executor:
    results = list(executor.map(download_img, image_urls.items()))

success = sum(1 for _, ok, _ in results if ok)
print(f"Downloaded {success}/{len(image_urls)} images.")
for fn, ok, msg in results:
    if not ok:
        print(f"Failed: {fn} -> {msg}")
